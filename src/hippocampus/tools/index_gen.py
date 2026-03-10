"""Unified index generator — four-phase pipeline orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import HippoConfig, load_config
from ..constants import HIPPO_DIR, INDEX_FILE
from ..tag_vocab import TagVocab, load_vocab, save_vocab, is_valid_new_tag
from ..utils import is_doc, is_hidden, read_json, write_json
from .index_gen_cache import (
    content_hash as _content_hash,
    load_phase1_cache as _load_phase1_cache,
    load_phase2_cache as _load_phase2_cache,
    load_phase3_cache as _load_phase3_cache,
    phase2_input_hash as _phase2_input_hash,
    phase3_module_input_hash as _phase3_module_input_hash,
    save_phase1_cache as _save_phase1_cache,
    save_phase2_cache as _save_phase2_cache,
    save_phase3_cache as _save_phase3_cache,
)
from .index_gen_local import (
    build_local_only_index as _build_local_only_index,
    detect_lang_hint as _detect_lang_hint,
    phase_0_local as _phase_0_local,
)
from .index_gen_phase2 import (
    phase2_assign_files as _phase2_assign_files_impl,
    phase2_full as _phase2_full_impl,
    phase2_partial_assign as _phase2_partial_assign_impl,
)
from .index_gen_phase2_incremental import phase2_incremental_impl as _phase2_incremental_impl
from .index_gen_phase1 import phase_1_impl as _phase_1_impl
from .index_gen_phase3 import (
    build_project_overview_impl as _build_project_overview_impl,
    phase3a_enrich_module_impl as _phase3a_enrich_module_impl,
)
from .index_gen_phase4 import phase_4_merge_impl as _phase_4_merge_impl
from .index_gen_dependencies import (
    compute_function_dependencies as _compute_function_dependencies_impl,
    compute_module_dependencies as _compute_module_dependencies_impl,
    resolve_import_to_file as _resolve_import_to_file_impl,
    resolve_relative_import as _resolve_relative_import_impl,
)
from .index_gen_runtime import (
    cleanup_llm_clients as _cleanup_llm_clients_impl,
    run_index_pipeline_impl as _run_index_pipeline_impl,
)


async def phase_0(
    target: Path,
    output_dir: Path,
    verbose: bool = False,
) -> dict[str, Any]:
    return await _phase_0_local(target, output_dir, verbose=verbose)


async def phase_1(
    config: HippoConfig,
    phase0_data: dict[str, Any],
    target: Path,
    output_dir: Path | None = None,
    dir_tree: str = "",
    verbose: bool = False,
) -> dict[str, dict]:
    return await _phase_1_impl(
        config=config,
        phase0_data=phase0_data,
        target=target,
        output_dir=output_dir,
        dir_tree=dir_tree,
        verbose=verbose,
        content_hash_fn=_content_hash,
        load_phase1_cache_fn=_load_phase1_cache,
        save_phase1_cache_fn=_save_phase1_cache,
        detect_lang_hint_fn=_detect_lang_hint,
    )


async def phase_2(
    config: HippoConfig,
    phase1_results: dict[str, dict],
    output_dir: Path | None = None,
    verbose: bool = False,
) -> tuple[list[dict], dict[str, str]]:
    return await _phase2_incremental_impl(
        phase1_results=phase1_results,
        output_dir=output_dir,
        verbose=verbose,
        phase2_input_hash_fn=_phase2_input_hash,
        load_phase2_cache_fn=_load_phase2_cache,
        content_hash_fn=_content_hash,
        phase2_partial_assign_fn=_phase2_partial_assign,
        phase2_full_fn=_phase2_full,
        save_phase2_cache_fn=_save_phase2_cache,
        config=config,
    )


async def _phase2_full(
    config: HippoConfig,
    phase1_results: dict[str, dict],
    verbose: bool = False,
) -> tuple[list[dict], dict[str, str]]:
    return await _phase2_full_impl(config, phase1_results, verbose)


async def _phase2_assign_files(
    config: HippoConfig,
    modules: list[dict],
    phase1_results: dict[str, dict],
    files_to_assign: set[str],
    verbose: bool = False,
) -> dict[str, str]:
    return await _phase2_assign_files_impl(
        config,
        modules,
        phase1_results,
        files_to_assign,
        verbose,
    )


async def _phase2_partial_assign(
    config: HippoConfig,
    modules: list[dict],
    delta_files: set[str],
    phase1_results: dict[str, dict],
    file_to_module: dict[str, str],
    verbose: bool = False,
) -> None:
    await _phase2_partial_assign_impl(
        config,
        modules,
        delta_files,
        phase1_results,
        file_to_module,
        verbose,
    )


async def phase_3(
    config: HippoConfig,
    modules: list[dict],
    file_to_module: dict[str, str],
    phase1_results: dict[str, dict],
    target: Path,
    output_dir: Path | None = None,
    verbose: bool = False,
) -> tuple[list[dict], dict]:
    """Phase 3: Incremental module descriptions + project overview.

    3a: Per-module desc + key_files (cached per module)
    3b: Project overview (cached by module summaries hash)
    Returns (enriched_modules, project_node).
    """
    from ..llm.client import HippoLLM
    llm_3 = HippoLLM(config)

    # Load cache
    cache: dict[str, Any] = {}
    if output_dir:
        cache = _load_phase3_cache(output_dir)
    cached_3a: dict[str, dict] = cache.get("phase_3a", {})
    cached_3b: dict[str, Any] = cache.get("phase_3b", {})

    # Group files by module
    module_files_map: dict[str, list[str]] = {}
    for fp, mid in file_to_module.items():
        module_files_map.setdefault(mid, []).append(fp)

    # Phase 3a: Per-module desc + key_files (with cache)
    enriched_modules = []
    reused_3a = 0
    called_3a = 0
    for mod in modules:
        mid = mod["id"]
        mod_files = module_files_map.get(mid, [])
        mod_hash = _phase3_module_input_hash(
            mid, mod.get("desc", ""), mod_files, phase1_results,
        )

        # Check cache
        cached_entry = cached_3a.get(mid)
        if cached_entry and cached_entry.get("hash") == mod_hash:
            enriched = dict(mod)
            enriched["file_count"] = len(mod_files)
            enriched.update(cached_entry["result"])
            enriched_modules.append(enriched)
            reused_3a += 1
            continue

        # Cache miss: call LLM
        called_3a += 1
        enriched = await _phase3a_enrich_module(
            llm_3, mod, mod_files, phase1_results,
        )
        enriched_modules.append(enriched)

        # Update cache
        cached_3a[mid] = {
            "hash": mod_hash,
            "result": {
                "desc": enriched.get("desc", ""),
                "key_files": enriched.get("key_files", []),
            },
        }

    # Prune removed modules from cache
    current_module_ids = {m["id"] for m in modules}
    for mid in list(cached_3a.keys()):
        if mid not in current_module_ids:
            del cached_3a[mid]

    if verbose:
        print(
            f"Phase 3a incremental: {reused_3a} cached, "
            f"{called_3a} LLM calls"
        )

    # Phase 3b: Project overview (with cache)
    module_summaries = "\n".join(
        f"- {m['id']}: {m.get('desc', '')}"
        for m in enriched_modules
    )
    summaries_hash = _content_hash(module_summaries)

    # Check 3b cache
    if (cached_3b.get("hash") == summaries_hash
            and cached_3b.get("result")):
        project_node = cached_3b["result"]
        # Update scale counts (they may change even if descriptions don't)
        project_node["scale"]["files"] = len(phase1_results)
        project_node["scale"]["modules"] = len(enriched_modules)
        if verbose:
            print("Phase 3b incremental: cache hit, 0 LLM calls")
    else:
        # Cache miss: call LLM for 3b
        if verbose:
            print("Phase 3b incremental: cache miss, calling LLM")
        project_node = await _build_project_overview_impl(
            llm_3,
            enriched_modules,
            phase1_results,
            target,
        )

        # Update 3b cache
        cached_3b = {"hash": summaries_hash, "result": project_node}

    # Persist Phase 3 cache
    if output_dir:
        _save_phase3_cache(output_dir, {
            "phase_3a": cached_3a,
            "phase_3b": cached_3b,
        })

    return enriched_modules, project_node


async def _phase3a_enrich_module(
    llm: Any,
    mod: dict,
    mod_files: list[str],
    phase1_results: dict[str, dict],
) -> dict:
    project_root = Path(llm.config.target).resolve() if hasattr(llm, "config") else None
    return await _phase3a_enrich_module_impl(
        llm,
        mod,
        mod_files,
        phase1_results,
        project_root=project_root,
    )


def _resolve_import_to_file(
    module_name: str,
    current_dir: str,
    files_index: dict[str, dict],
    target: Path,
) -> list[str]:
    return _resolve_import_to_file_impl(module_name, current_dir, files_index, target)


def _resolve_relative_import(
    module_name: str,
    level: int,
    current_dir: str,
    files_index: dict[str, dict],
    target: Path,
) -> list[str]:
    return _resolve_relative_import_impl(
        module_name, level, current_dir, files_index, target
    )


def _compute_function_dependencies(
    files_index: dict[str, dict],
    target: Path,
) -> dict[str, list[dict[str, Any]]]:
    return _compute_function_dependencies_impl(files_index, target)


def _compute_module_dependencies(
    files_index: dict[str, dict],
    file_to_module: dict[str, str],
    target: Path,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[str]]]:
    return _compute_module_dependencies_impl(files_index, file_to_module, target)


def phase_4_merge(
    phase0_data: dict[str, Any],
    phase1_results: dict[str, dict],
    modules: list[dict],
    file_to_module: dict[str, str],
    project_node: dict,
    target: Path | None = None,
    local_only: bool = False,
) -> dict:
    if local_only:
        return _build_local_only_index(
            phase0_data,
            target,
            merge_fn=phase_4_merge,
        )
    return _phase_4_merge_impl(
        phase0_data=phase0_data,
        phase1_results=phase1_results,
        modules=modules,
        file_to_module=file_to_module,
        project_node=project_node,
        compute_module_dependencies_fn=_compute_module_dependencies,
        compute_function_dependencies_fn=_compute_function_dependencies,
        target=target,
    )


async def _cleanup_llm_clients():
    await _cleanup_llm_clients_impl()


async def run_index_pipeline(
    target: Path,
    output_dir: Path,
    config: HippoConfig,
    phase: int | None = None,
    verbose: bool = False,
    no_llm: bool = False,
) -> dict | None:
    return await _run_index_pipeline_impl(
        target=target,
        output_dir=output_dir,
        phase=phase,
        verbose=verbose,
        no_llm=no_llm,
        phase_0_fn=phase_0,
        phase_1_fn=phase_1,
        phase_2_fn=phase_2,
        phase_3_fn=phase_3,
        phase_4_merge_fn=phase_4_merge,
        cleanup_fn=_cleanup_llm_clients,
        config=config,
    )
