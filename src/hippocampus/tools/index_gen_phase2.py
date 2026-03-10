"""Phase 2 module clustering helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import HippoConfig
from .index_gen_cache import (
    content_hash as _content_hash,
    load_phase2_cache as _load_phase2_cache,
    phase2_input_hash as _phase2_input_hash,
    save_phase2_cache as _save_phase2_cache,
)


async def phase_2_impl(
    config: HippoConfig,
    phase1_results: dict[str, dict],
    output_dir: Path | None = None,
    verbose: bool = False,
) -> tuple[list[dict], dict[str, str]]:
    """Phase 2: Incremental module clustering."""
    current_hash = _phase2_input_hash(phase1_results)
    cache: dict[str, Any] = {}
    if output_dir:
        cache = _load_phase2_cache(output_dir)

    cached_hash = cache.get("input_hash", "")
    cached_modules = cache.get("modules", [])
    cached_file_to_module: dict[str, str] = cache.get("file_to_module", {})
    cached_file_hashes: dict[str, str] = cache.get("file_hashes", {})

    current_file_hashes: dict[str, str] = {}
    for fp, data in phase1_results.items():
        desc = data.get("desc", "")
        tags = ",".join(sorted(data.get("tags", [])))
        current_file_hashes[fp] = _content_hash(f"{fp}|{desc}|{tags}")

    current_files = set(phase1_results.keys())
    cached_files = set(cached_file_hashes.keys())
    added_files = current_files - cached_files
    removed_files = cached_files - current_files
    changed_files = {
        fp
        for fp in current_files & cached_files
        if current_file_hashes[fp] != cached_file_hashes.get(fp, "")
    }
    delta_files = added_files | changed_files

    if (
        current_hash == cached_hash
        and cached_modules
        and not delta_files
        and not removed_files
    ):
        if verbose:
            print("Phase 2 incremental: full cache hit, 0 LLM calls")
        return cached_modules, cached_file_to_module

    change_ratio = len(delta_files) / max(len(current_files), 1)
    can_partial = cached_modules and change_ratio < 0.2 and not removed_files

    if can_partial:
        if verbose:
            print(
                f"Phase 2 incremental: partial hit, "
                f"{len(delta_files)} files to re-assign, "
                f"reusing {len(cached_modules)} modules"
            )
        modules = cached_modules
        file_to_module = dict(cached_file_to_module)
        await phase2_partial_assign(
            config,
            modules,
            delta_files,
            phase1_results,
            file_to_module,
            verbose,
        )
    else:
        if verbose:
            print(
                f"Phase 2 incremental: cache miss "
                f"(change_ratio={change_ratio:.1%}, "
                f"added={len(added_files)}, changed={len(changed_files)}, "
                f"removed={len(removed_files)}), full LLM calls"
            )
        modules, file_to_module = await phase2_full(config, phase1_results, verbose)

    if output_dir:
        _save_phase2_cache(
            output_dir,
            {
                "input_hash": current_hash,
                "modules": modules,
                "file_to_module": file_to_module,
                "file_hashes": current_file_hashes,
            },
        )

    return modules, file_to_module


async def phase2_full(
    config: HippoConfig,
    phase1_results: dict[str, dict],
    verbose: bool = False,
) -> tuple[list[dict], dict[str, str]]:
    """Run full Phase 2a + 2b LLM calls."""
    from ..llm.client import HippoLLM
    from ..llm.prompts import PHASE_2A_SYSTEM, PHASE_2A_USER
    from ..llm.validators import _try_parse_json, validate_phase_2a

    del verbose
    llm = HippoLLM(config)

    summaries = []
    for fp, data in phase1_results.items():
        desc = data.get("desc", "")
        tags = data.get("tags", [])
        summaries.append(f"{fp}: {desc} [{', '.join(tags)}]")
    file_summaries = "\n".join(summaries)

    msg_2a = [
        {"role": "system", "content": PHASE_2A_SYSTEM},
        {"role": "user", "content": PHASE_2A_USER.format(file_summaries=file_summaries[:40000])},
    ]
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
    from ..llm.client import HippoLLM
    from ..llm.prompts import PHASE_2B_SYSTEM, PHASE_2B_USER
    from ..llm.validators import _try_parse_json, validate_phase_2b

    del verbose
    llm = HippoLLM(config)
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

    msg_2b = [
        {"role": "system", "content": PHASE_2B_SYSTEM},
        {
            "role": "user",
            "content": PHASE_2B_USER.format(
                module_vocab=module_vocab,
                file_summaries=file_summaries[:40000],
                file_count=file_count,
            ),
        },
    ]

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
