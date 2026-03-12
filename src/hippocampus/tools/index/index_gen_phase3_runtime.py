"""Phase 3 orchestration helpers for index generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _group_files_by_module(file_to_module: dict[str, str]) -> dict[str, list[str]]:
    module_files_map: dict[str, list[str]] = {}
    for file_path, module_id in file_to_module.items():
        module_files_map.setdefault(module_id, []).append(file_path)
    return module_files_map


def _phase3a_hash(
    mod: dict,
    mod_files: list[str],
    phase1_results: dict[str, dict],
    phase3_module_input_hash_fn,
) -> str:
    return phase3_module_input_hash_fn(
        mod["id"],
        mod.get("desc", ""),
        mod_files,
        phase1_results,
    )


def _cached_module_result(mod: dict, mod_files: list[str], cached_entry: dict[str, Any]) -> dict:
    enriched = dict(mod)
    enriched["file_count"] = len(mod_files)
    enriched.update(cached_entry["result"])
    return enriched


async def _enrich_modules(
    modules: list[dict],
    *,
    cached_3a: dict[str, dict],
    module_files_map: dict[str, list[str]],
    phase1_results: dict[str, dict],
    phase3_module_input_hash_fn,
    phase3a_enrich_module_fn,
    llm_3,
) -> tuple[list[dict], int, int]:
    enriched_modules: list[dict] = []
    reused_3a = 0
    called_3a = 0
    for mod in modules:
        enriched, cache_hit = await _enrich_single_module(
            mod,
            cached_3a=cached_3a,
            module_files_map=module_files_map,
            phase1_results=phase1_results,
            phase3_module_input_hash_fn=phase3_module_input_hash_fn,
            phase3a_enrich_module_fn=phase3a_enrich_module_fn,
            llm_3=llm_3,
        )
        enriched_modules.append(enriched)
        reused_3a += int(cache_hit)
        called_3a += int(not cache_hit)
    return enriched_modules, reused_3a, called_3a


async def _enrich_single_module(
    mod: dict,
    *,
    cached_3a: dict[str, dict],
    module_files_map: dict[str, list[str]],
    phase1_results: dict[str, dict],
    phase3_module_input_hash_fn,
    phase3a_enrich_module_fn,
    llm_3,
) -> tuple[dict, bool]:
    module_id = mod["id"]
    mod_files = module_files_map.get(module_id, [])
    mod_hash = _phase3a_hash(mod, mod_files, phase1_results, phase3_module_input_hash_fn)
    cached_entry = cached_3a.get(module_id)
    if cached_entry and cached_entry.get("hash") == mod_hash:
        return _cached_module_result(mod, mod_files, cached_entry), True

    enriched = await phase3a_enrich_module_fn(llm_3, mod, mod_files, phase1_results)
    cached_3a[module_id] = {
        "hash": mod_hash,
        "result": {
            "desc": enriched.get("desc", ""),
            "key_files": enriched.get("key_files", []),
        },
    }
    return enriched, False


def _prune_removed_modules(cached_3a: dict[str, dict], modules: list[dict]) -> None:
    current_module_ids = {module["id"] for module in modules}
    for module_id in list(cached_3a.keys()):
        if module_id not in current_module_ids:
            del cached_3a[module_id]


async def _build_project_node(
    enriched_modules: list[dict],
    *,
    cached_3b: dict[str, Any],
    phase1_results: dict[str, dict],
    target: Path,
    verbose: bool,
    content_hash_fn,
    build_project_overview_fn,
    llm_3,
) -> tuple[dict[str, Any], dict[str, Any]]:
    module_summaries = "\n".join(
        f"- {module['id']}: {module.get('desc', '')}"
        for module in enriched_modules
    )
    summaries_hash = content_hash_fn(module_summaries)
    if cached_3b.get("hash") == summaries_hash and cached_3b.get("result"):
        project_node = cached_3b["result"]
        project_node["scale"]["files"] = len(phase1_results)
        project_node["scale"]["modules"] = len(enriched_modules)
        if verbose:
            print("Phase 3b incremental: cache hit, 0 LLM calls")
        return project_node, cached_3b

    if verbose:
        print("Phase 3b incremental: cache miss, calling LLM")
    project_node = await build_project_overview_fn(
        llm_3,
        enriched_modules,
        phase1_results,
        target,
    )
    return project_node, {"hash": summaries_hash, "result": project_node}


def _save_phase3_cache(
    output_dir: Path | None,
    cached_3a: dict[str, dict],
    cached_3b: dict[str, Any],
    save_phase3_cache_fn,
) -> None:
    if output_dir:
        save_phase3_cache_fn(
            output_dir,
            {
                "phase_3a": cached_3a,
                "phase_3b": cached_3b,
            },
        )


async def phase_3_impl(
    *,
    config,
    modules: list[dict],
    file_to_module: dict[str, str],
    phase1_results: dict[str, dict],
    target: Path,
    output_dir: Path | None,
    verbose: bool,
    load_phase3_cache_fn,
    phase3_module_input_hash_fn,
    content_hash_fn,
    phase3a_enrich_module_fn,
    build_project_overview_fn,
    save_phase3_cache_fn,
) -> tuple[list[dict], dict[str, Any]]:
    from ...llm.client import HippoLLM

    llm_3 = HippoLLM(config)
    cache: dict[str, Any] = load_phase3_cache_fn(output_dir) if output_dir else {}
    cached_3a: dict[str, dict] = cache.get("phase_3a", {})
    cached_3b: dict[str, Any] = cache.get("phase_3b", {})

    enriched_modules, reused_3a, called_3a = await _enrich_modules(
        modules,
        cached_3a=cached_3a,
        module_files_map=_group_files_by_module(file_to_module),
        phase1_results=phase1_results,
        phase3_module_input_hash_fn=phase3_module_input_hash_fn,
        phase3a_enrich_module_fn=phase3a_enrich_module_fn,
        llm_3=llm_3,
    )
    _prune_removed_modules(cached_3a, modules)
    if verbose:
        print(f"Phase 3a incremental: {reused_3a} cached, {called_3a} LLM calls")

    project_node, cached_3b = await _build_project_node(
        enriched_modules,
        cached_3b=cached_3b,
        phase1_results=phase1_results,
        target=target,
        verbose=verbose,
        content_hash_fn=content_hash_fn,
        build_project_overview_fn=build_project_overview_fn,
        llm_3=llm_3,
    )
    _save_phase3_cache(output_dir, cached_3a, cached_3b, save_phase3_cache_fn)
    return enriched_modules, project_node
