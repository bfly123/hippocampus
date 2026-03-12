"""Phase 2 module clustering helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...config import HippoConfig
from .index_gen_cache import (
    content_hash as _content_hash,
    load_phase2_cache as _load_phase2_cache,
    phase2_input_hash as _phase2_input_hash,
    save_phase2_cache as _save_phase2_cache,
)
from .index_gen_phase2_runtime import phase_2_impl_runtime


async def phase_2_impl(
    config: HippoConfig,
    phase1_results: dict[str, dict],
    output_dir: Path | None = None,
    verbose: bool = False,
) -> tuple[list[dict], dict[str, str]]:
    """Phase 2: Incremental module clustering."""
    return await phase_2_impl_runtime(
        config=config,
        phase1_results=phase1_results,
        output_dir=output_dir,
        verbose=verbose,
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
) -> tuple[list[dict], dict[str, str]]:
    """Run full Phase 2a + 2b LLM calls."""
    from ...llm.client import HippoLLM
    from ...llm.prompts import build_phase_2a_messages
    from ...llm.validators import _try_parse_json, validate_phase_2a

    del verbose
    llm = HippoLLM(config)
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
    text_2a, _ = await llm.call_with_retry("phase_2a", msg_2a, validate_phase_2a)
    modules_data, _ = _try_parse_json(text_2a)
    modules = modules_data.get("modules", []) if modules_data else []

    file_to_module = await phase2_assign_files(
        config,
        modules,
        phase1_results,
        set(phase1_results.keys()),
        verbose=False,
    )
    return modules, file_to_module


async def phase2_assign_files(
    config: HippoConfig,
    modules: list[dict],
    phase1_results: dict[str, dict],
    files_to_assign: set[str],
    verbose: bool = False,
) -> dict[str, str]:
    """Run Phase 2b: assign a set of files to modules via LLM."""
    from ...llm.client import HippoLLM
    from ...llm.prompts import build_phase_2b_messages
    from ...llm.validators import _try_parse_json, validate_phase_2b

    del verbose
    llm = HippoLLM(config)
    project_root = Path(config.target).resolve()
    valid_ids = {m["id"] for m in modules}
    module_vocab = "\n".join(f"- {m['id']}: {m.get('desc', '')}" for m in modules)

    summaries = []
    for fp in sorted(files_to_assign):
        data = phase1_results.get(fp, {})
        desc = data.get("desc", "")
        tags = data.get("tags", [])
        summaries.append(f"{fp}: {desc} [{', '.join(tags)}]")
    file_summaries = "\n".join(summaries)
    file_count = len(files_to_assign)

    msg_2b = build_phase_2b_messages(
        project_root=project_root,
        module_vocab=module_vocab,
        file_summaries=file_summaries[:40000],
        file_count=file_count,
    )

    def validator_2b(text):
        return validate_phase_2b(text, file_count, valid_ids)

    text_2b, _ = await llm.call_with_retry("phase_2b", msg_2b, validator_2b)
    assignments, _ = _try_parse_json(text_2b)

    file_to_module: dict[str, str] = {}
    if isinstance(assignments, list):
        for item in assignments:
            fp = item.get("file", "")
            mid = item.get("module_id", "")
            if fp and mid:
                file_to_module[fp] = mid
    return file_to_module


async def phase2_partial_assign(
    config: HippoConfig,
    modules: list[dict],
    delta_files: set[str],
    phase1_results: dict[str, dict],
    file_to_module: dict[str, str],
    verbose: bool = False,
) -> None:
    """Re-assign only delta files, mutating file_to_module in place."""
    new_assignments = await phase2_assign_files(
        config,
        modules,
        phase1_results,
        delta_files,
        verbose,
    )
    file_to_module.update(new_assignments)
