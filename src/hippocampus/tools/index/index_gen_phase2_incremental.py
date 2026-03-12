from __future__ import annotations

from typing import Any


def _current_file_hashes(
    phase1_results: dict[str, dict],
    content_hash_fn,
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for file_path, data in phase1_results.items():
        desc = data.get("desc", "")
        tags = ",".join(sorted(data.get("tags", [])))
        hashes[file_path] = content_hash_fn(f"{file_path}|{desc}|{tags}")
    return hashes


def _delta_files(
    phase1_results: dict[str, dict],
    cached_file_hashes: dict[str, str],
    content_hash_fn,
) -> tuple[dict[str, str], set[str], set[str], set[str]]:
    current_file_hashes = _current_file_hashes(phase1_results, content_hash_fn)
    current_files = set(phase1_results)
    cached_files = set(cached_file_hashes)
    added_files = current_files - cached_files
    removed_files = cached_files - current_files
    changed_files = {
        file_path
        for file_path in current_files & cached_files
        if current_file_hashes[file_path] != cached_file_hashes.get(file_path, "")
    }
    return current_file_hashes, added_files, removed_files, changed_files


def _log_partial_hit(
    *,
    verbose: bool,
    delta_files: set[str],
    cached_modules: list[dict],
) -> None:
    if verbose:
        print(
            f"Phase 2 incremental: partial hit, {len(delta_files)} files to re-assign, "
            f"reusing {len(cached_modules)} modules"
        )


def _log_cache_miss(
    *,
    verbose: bool,
    change_ratio: float,
    added_files: set[str],
    changed_files: set[str],
    removed_files: set[str],
) -> None:
    if verbose:
        print(
            f"Phase 2 incremental: cache miss (change_ratio={change_ratio:.1%}, "
            f"added={len(added_files)}, changed={len(changed_files)}, "
            f"removed={len(removed_files)}), full LLM calls"
        )


async def phase2_incremental_impl(
    *,
    phase1_results: dict[str, dict],
    output_dir,
    verbose: bool,
    phase2_input_hash_fn,
    load_phase2_cache_fn,
    content_hash_fn,
    phase2_partial_assign_fn,
    phase2_full_fn,
    save_phase2_cache_fn,
    config,
) -> tuple[list[dict], dict[str, str]]:
    current_hash = phase2_input_hash_fn(phase1_results)
    cache: dict[str, Any] = load_phase2_cache_fn(output_dir) if output_dir else {}
    cached_modules = cache.get("modules", [])
    cached_file_to_module: dict[str, str] = cache.get("file_to_module", {})
    cached_file_hashes: dict[str, str] = cache.get("file_hashes", {})

    current_file_hashes, added_files, removed_files, changed_files = _delta_files(
        phase1_results,
        cached_file_hashes,
        content_hash_fn,
    )
    delta_files = added_files | changed_files
    if (
        current_hash == cache.get("input_hash", "")
        and cached_modules
        and not delta_files
        and not removed_files
    ):
        if verbose:
            print("Phase 2 incremental: full cache hit, 0 LLM calls")
        return cached_modules, cached_file_to_module

    change_ratio = len(delta_files) / max(len(phase1_results), 1)
    can_partial = cached_modules and change_ratio < 0.2 and not removed_files
    if can_partial:
        _log_partial_hit(
            verbose=verbose,
            delta_files=delta_files,
            cached_modules=cached_modules,
        )
        modules = cached_modules
        file_to_module = dict(cached_file_to_module)
        await phase2_partial_assign_fn(
            config,
            modules,
            delta_files,
            phase1_results,
            file_to_module,
            verbose,
        )
    else:
        _log_cache_miss(
            verbose=verbose,
            change_ratio=change_ratio,
            added_files=added_files,
            changed_files=changed_files,
            removed_files=removed_files,
        )
        modules, file_to_module = await phase2_full_fn(config, phase1_results, verbose)

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
