"""Incremental runtime helpers for phase 2 clustering."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _current_file_hashes(phase1_results: dict[str, dict], *, content_hash_fn) -> dict[str, str]:
    current_hashes: dict[str, str] = {}
    for file_path, data in phase1_results.items():
        desc = data.get("desc", "")
        tags = ",".join(sorted(data.get("tags", [])))
        current_hashes[file_path] = content_hash_fn(f"{file_path}|{desc}|{tags}")
    return current_hashes


def _delta_sets(
    phase1_results: dict[str, dict],
    *,
    cached_file_hashes: dict[str, str],
    current_file_hashes: dict[str, str],
) -> tuple[set[str], set[str], set[str]]:
    current_files = set(phase1_results.keys())
    cached_files = set(cached_file_hashes.keys())
    added_files = current_files - cached_files
    removed_files = cached_files - current_files
    changed_files = {
        file_path
        for file_path in current_files & cached_files
        if current_file_hashes[file_path] != cached_file_hashes.get(file_path, "")
    }
    return added_files, removed_files, changed_files


def _cache_hit(
    *,
    current_hash: str,
    cached_hash: str,
    cached_modules: list[dict],
    delta_files: set[str],
    removed_files: set[str],
) -> bool:
    return current_hash == cached_hash and bool(cached_modules) and not delta_files and not removed_files


def _can_partial_reassign(
    *,
    cached_modules: list[dict],
    delta_files: set[str],
    removed_files: set[str],
    total_files: int,
) -> bool:
    change_ratio = len(delta_files) / max(total_files, 1)
    return (
        bool(cached_modules)
        and change_ratio < 0.3
        and len(delta_files) < 100
        and not removed_files
    )


async def phase_2_impl_runtime(
    *,
    config,
    phase1_results: dict[str, dict],
    output_dir: Path | None,
    verbose: bool,
    phase2_input_hash_fn,
    load_phase2_cache_fn,
    content_hash_fn,
    partial_assign_fn,
    full_phase2_fn,
    save_phase2_cache_fn,
) -> tuple[list[dict], dict[str, str]]:
    current_hash = phase2_input_hash_fn(phase1_results)
    cache: dict[str, Any] = load_phase2_cache_fn(output_dir) if output_dir else {}
    cached_hash = cache.get("input_hash", "")
    cached_modules = cache.get("modules", [])
    cached_file_to_module: dict[str, str] = cache.get("file_to_module", {})
    cached_file_hashes: dict[str, str] = cache.get("file_hashes", {})

    current_file_hashes = _current_file_hashes(
        phase1_results,
        content_hash_fn=content_hash_fn,
    )
    added_files, removed_files, changed_files = _delta_sets(
        phase1_results,
        cached_file_hashes=cached_file_hashes,
        current_file_hashes=current_file_hashes,
    )
    delta_files = added_files | changed_files

    if _cache_hit(
        current_hash=current_hash,
        cached_hash=cached_hash,
        cached_modules=cached_modules,
        delta_files=delta_files,
        removed_files=removed_files,
    ):
        if verbose:
            print("Phase 2 incremental: full cache hit, 0 LLM calls")
        return cached_modules, cached_file_to_module

    if _can_partial_reassign(
        cached_modules=cached_modules,
        delta_files=delta_files,
        removed_files=removed_files,
        total_files=len(phase1_results),
    ):
        if verbose:
            print(
                f"Phase 2 incremental: partial hit, {len(delta_files)} files to re-assign, "
                f"reusing {len(cached_modules)} modules"
            )
        modules = cached_modules
        file_to_module = dict(cached_file_to_module)
        await partial_assign_fn(
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
                "Phase 2 incremental: cache miss "
                f"(change_ratio={len(delta_files) / max(len(phase1_results), 1):.1%}, "
                f"added={len(added_files)}, changed={len(changed_files)}, removed={len(removed_files)}), "
                "full LLM calls"
            )
        modules, file_to_module = await full_phase2_fn(config, phase1_results, verbose)

    if output_dir:
        save_phase2_cache_fn(
            output_dir,
            {
                "input_hash": current_hash,
                "modules": modules,
                "file_to_module": file_to_module,
                "file_hashes": current_file_hashes,
            },
        )

    return modules, file_to_module
