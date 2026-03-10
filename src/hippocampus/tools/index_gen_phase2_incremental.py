from __future__ import annotations

from typing import Any


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
    cache: dict[str, Any] = {}
    if output_dir:
        cache = load_phase2_cache_fn(output_dir)

    cached_hash = cache.get("input_hash", "")
    cached_modules = cache.get("modules", [])
    cached_file_to_module: dict[str, str] = cache.get("file_to_module", {})
    cached_file_hashes: dict[str, str] = cache.get("file_hashes", {})

    current_file_hashes: dict[str, str] = {}
    for fp, data in phase1_results.items():
        desc = data.get("desc", "")
        tags = ",".join(sorted(data.get("tags", [])))
        current_file_hashes[fp] = content_hash_fn(f"{fp}|{desc}|{tags}")

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

    if current_hash == cached_hash and cached_modules and not delta_files and not removed_files:
        if verbose:
            print("Phase 2 incremental: full cache hit, 0 LLM calls")
        return cached_modules, cached_file_to_module

    change_ratio = len(delta_files) / max(len(current_files), 1)
    can_partial = cached_modules and change_ratio < 0.2 and not removed_files
    if can_partial:
        if verbose:
            print(
                f"Phase 2 incremental: partial hit, {len(delta_files)} files to re-assign, "
                f"reusing {len(cached_modules)} modules"
            )
        modules = cached_modules
        file_to_module = dict(cached_file_to_module)
        await phase2_partial_assign_fn(
            config, modules, delta_files, phase1_results, file_to_module, verbose
        )
    else:
        if verbose:
            print(
                f"Phase 2 incremental: cache miss (change_ratio={change_ratio:.1%}, "
                f"added={len(added_files)}, changed={len(changed_files)}, "
                f"removed={len(removed_files)}), full LLM calls"
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
