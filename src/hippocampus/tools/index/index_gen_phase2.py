"""Phase 2 module clustering helpers."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from llmgateway import TaskRequest, Validator

from ...config import HippoConfig
from ...llm.gateway import create_llm_gateway
from .index_gen_cache import (
    content_hash as _content_hash,
    load_phase2_cache as _load_phase2_cache,
    phase2_input_hash as _phase2_input_hash,
    save_phase2_cache as _save_phase2_cache,
)
from .index_gen_progress import run_json_requests_with_progress
from .index_gen_reporting import format_phase_duration, format_progress_line
from .index_gen_phase2_runtime import phase_2_impl_runtime

_PHASE2B_BATCH_SIZE = 64
_PHASE2B_MAX_SUMMARY_CHARS = 12000


async def phase_2_impl(
    config: HippoConfig,
    phase1_results: dict[str, dict],
    output_dir: Path | None = None,
    verbose: bool = False,
    show_progress: bool = False,
) -> tuple[list[dict], dict[str, str]]:
    """Phase 2: Incremental module clustering."""
    return await phase_2_impl_runtime(
        config=config,
        phase1_results=phase1_results,
        output_dir=output_dir,
        verbose=verbose,
        show_progress=show_progress,
        phase2_input_hash_fn=_phase2_input_hash,
        load_phase2_cache_fn=_load_phase2_cache,
        content_hash_fn=_content_hash,
        partial_assign_fn=phase2_partial_assign,
        full_phase2_fn=phase2_full,
        save_phase2_cache_fn=_save_phase2_cache,
    )


async def phase2_full(
    config: HippoConfig,
    phase1_results: dict[str, dict],
    verbose: bool = False,
    show_progress: bool = False,
) -> tuple[list[dict], dict[str, str]]:
    """Run full Phase 2a + 2b LLM calls."""
    from ...llm.prompts import build_phase_2a_messages
    from ...llm.validators import validate_phase_2a

    llm = create_llm_gateway(config)
    project_root = Path(config.target).resolve()

    summaries = []
    for fp, data in phase1_results.items():
        desc = data.get("desc", "")
        tags = data.get("tags", [])
        summaries.append(f"{fp}: {desc} [{', '.join(tags)}]")
    file_summaries = "\n".join(summaries)

    msg_2a = build_phase_2a_messages(
        project_root=project_root,
        file_summaries=file_summaries[:40000],
    )
    if verbose or show_progress:
        print(f"Phase 2a: clustering {len(phase1_results)} file summaries")
    if verbose:
        print(
            f"Phase 2a plan: {len(phase1_results)} file summaries, "
            f"{len(file_summaries)} chars before trim, "
            f"{len(file_summaries[:40000])} chars sent"
        )
        print(format_progress_line("Phase 2a", 0, 1, detail="global clustering request"))
    started = time.perf_counter()
    result_2a = await llm.run_json_task_with_retry("phase_2a", msg_2a, validate_phase_2a)
    modules_data = result_2a.data if isinstance(result_2a.data, dict) else None
    modules = modules_data.get("modules", []) if modules_data else []
    if verbose or show_progress:
        print(
            format_progress_line(
                "Phase 2a",
                1,
                1,
                detail=f"{len(modules)} modules, {format_phase_duration(time.perf_counter() - started)}",
            )
        )

    file_to_module = await phase2_assign_files(
        config,
        modules,
        phase1_results,
        set(phase1_results.keys()),
        verbose=verbose,
        show_progress=show_progress,
    )
    return modules, file_to_module


async def phase2_assign_files(
    config: HippoConfig,
    modules: list[dict],
    phase1_results: dict[str, dict],
    files_to_assign: set[str],
    verbose: bool = False,
    show_progress: bool = False,
) -> dict[str, str]:
    """Run Phase 2b: assign a set of files to modules via LLM."""
    llm = create_llm_gateway(config)
    file_to_module: dict[str, str] = {}
    requests, validators, batch_files = build_phase2b_requests(
        config,
        modules,
        phase1_results,
        files_to_assign,
    )
    if verbose or show_progress:
        print(
            f"Phase 2b: assigning {len(files_to_assign)} file(s) to {len(modules)} module(s)"
        )
    if verbose:
        batch_sizes = [len(batch) for batch in batch_files]
        print(
            f"Phase 2b plan: {len(files_to_assign)} files across {len(batch_files)} batch(es); "
            f"batch_sizes={batch_sizes}"
        )
    results = await run_json_requests_with_progress(
        llm=llm,
        requests=requests,
        validators=validators,
        verbose=verbose,
        show_progress=show_progress,
        label="Phase 2b",
        detail=f"{len(files_to_assign)} files",
    )

    for result_item, files_batch in zip(results, batch_files):
        if result_item.errors:
            continue
        file_to_module.update(
            apply_phase2b_response(
                result_item.data,
                files_batch=files_batch,
            )
        )
    return file_to_module


async def phase2_partial_assign(
    config: HippoConfig,
    modules: list[dict],
    delta_files: set[str],
    phase1_results: dict[str, dict],
    file_to_module: dict[str, str],
    verbose: bool = False,
    show_progress: bool = False,
) -> None:
    """Re-assign only delta files, mutating file_to_module in place."""
    if verbose or show_progress:
        print(
            f"Phase 2 partial reassign: {len(delta_files)} changed file(s), "
            f"reusing {len(modules)} module(s)"
        )
    new_assignments = await phase2_assign_files(
        config,
        modules,
        phase1_results,
        delta_files,
        verbose,
        show_progress=show_progress,
    )
    file_to_module.update(new_assignments)


def build_phase2b_requests(
    config: HippoConfig,
    modules: list[dict],
    phase1_results: dict[str, dict],
    files_to_assign: set[str],
) -> tuple[list[TaskRequest], list[Validator], list[list[str]]]:
    from ...llm.prompts import build_phase_2b_messages
    from ...llm.validators import validate_phase_2b

    project_root = Path(config.target).resolve()
    valid_ids = {m["id"] for m in modules}
    module_vocab = "\n".join(f"- {m['id']}: {m.get('desc', '')}" for m in modules)
    file_batches = _phase2b_batches(phase1_results, files_to_assign)

    requests: list[TaskRequest] = []
    validators: list[Validator] = []
    normalized_batches: list[list[str]] = []

    for files_batch, file_summaries in file_batches:
        requests.append(
            TaskRequest(
                task="phase_2b",
                messages=build_phase_2b_messages(
                    project_root=project_root,
                    module_vocab=module_vocab,
                    file_summaries=file_summaries,
                    file_count=len(files_batch),
                ),
            )
        )

        def validator_2b(
            text: str,
            *,
            expected_count: int = len(files_batch),
            valid_module_ids: set[str] = valid_ids,
        ) -> list[str]:
            return validate_phase_2b(text, expected_count, valid_module_ids)

        validators.append(validator_2b)
        normalized_batches.append(files_batch)

    return requests, validators, normalized_batches


def apply_phase2b_response(
    response_data: dict | list | None,
    *,
    files_batch: list[str],
) -> dict[str, str]:
    allowed_files = set(files_batch)
    file_to_module: dict[str, str] = {}
    if isinstance(response_data, list):
        for item in response_data:
            fp = item.get("file", "")
            mid = item.get("module_id", "")
            if fp and mid and fp in allowed_files:
                file_to_module[fp] = mid
    return file_to_module


def _phase2b_batches(
    phase1_results: dict[str, dict],
    files_to_assign: set[str],
) -> list[tuple[list[str], str]]:
    batches: list[tuple[list[str], str]] = []
    current_files: list[str] = []
    current_lines: list[str] = []
    current_chars = 0

    for fp in sorted(files_to_assign):
        data = phase1_results.get(fp, {})
        desc = data.get("desc", "")
        tags = data.get("tags", [])
        line = f"{fp}: {desc} [{', '.join(tags)}]"
        projected_chars = current_chars + len(line) + (1 if current_lines else 0)
        if current_files and (
            len(current_files) >= _PHASE2B_BATCH_SIZE
            or projected_chars > _PHASE2B_MAX_SUMMARY_CHARS
        ):
            batches.append((list(current_files), "\n".join(current_lines)))
            current_files = []
            current_lines = []
            current_chars = 0

        current_files.append(fp)
        current_lines.append(line)
        current_chars += len(line) + (1 if len(current_lines) > 1 else 0)

    if current_files:
        batches.append((list(current_files), "\n".join(current_lines)))

    return batches
