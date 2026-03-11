from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from ..constants import INDEX_FILE, TREE_FILE
from ..llm.transport import close_http_clients
from ..types import TreeNode
from ..utils import read_json, write_json
from .index_gen_reporting import format_phase_duration


async def cleanup_llm_clients() -> None:
    """Close shared HTTP clients used by hippo LLM transport."""
    try:
        await close_http_clients()
    except Exception:
        pass


async def run_index_pipeline_impl(
    target: Path,
    output_dir: Path,
    phase: int | None,
    verbose: bool,
    no_llm: bool,
    phase_0_fn: Callable[[Path, Path, bool], Awaitable[dict[str, Any]]],
    phase_1_fn: Callable[..., Awaitable[dict[str, dict]]],
    phase_2_fn: Callable[..., Awaitable[tuple[list[dict], dict[str, str]]]],
    phase_3_fn: Callable[..., Awaitable[tuple[list[dict], dict]]],
    phase_4_merge_fn: Callable[..., dict],
    cleanup_fn: Callable[[], Awaitable[None]],
    config: Any,
) -> dict | None:
    def log_phase_done(label: str, start_time: float) -> None:
        if verbose:
            print(f"{label} done in {format_phase_duration(time.perf_counter() - start_time)}")

    dir_tree = ""
    tree_path = output_dir / TREE_FILE
    if tree_path.exists():
        tree_data = read_json(tree_path)
        from .structure_prompt import _render_node

        root = TreeNode(**tree_data["root"])
        dir_tree = _render_node(root)

    phase0_data = None
    if phase is None or phase >= 0:
        if verbose:
            print("Phase 0: Local extraction ...")
        started = time.perf_counter()
        phase0_data = await phase_0_fn(target, output_dir, verbose)
        log_phase_done("Phase 0", started)
        if phase == 0:
            return None

    if no_llm:
        if verbose:
            print("Local-only mode: skipping LLM phases ...")
        index = phase_4_merge_fn(
            phase0_data=phase0_data,
            phase1_results={},
            modules=[],
            file_to_module={},
            project_node={},
            target=target,
            local_only=True,
        )
        out_path = output_dir / INDEX_FILE
        write_json(out_path, index)
        return index

    phase1_results = None
    if phase is None or phase >= 1:
        if verbose:
            print("Phase 1: Per-file LLM analysis ...")
        started = time.perf_counter()
        phase1_results = await phase_1_fn(
            config,
            phase0_data,
            target,
            output_dir=output_dir,
            dir_tree=dir_tree,
            verbose=verbose,
        )
        log_phase_done("Phase 1", started)
        if phase == 1:
            return None

    modules = None
    file_to_module = None
    if phase is None or phase >= 2:
        if verbose:
            print("Phase 2: Module clustering ...")
        started = time.perf_counter()
        modules, file_to_module = await phase_2_fn(
            config,
            phase1_results,
            output_dir=output_dir,
            verbose=verbose,
        )
        log_phase_done("Phase 2", started)
        if phase == 2:
            return None

    project_node = None
    if phase is None or phase >= 3:
        if verbose:
            print("Phase 3: Module descriptions + project overview ...")
        started = time.perf_counter()
        modules, project_node = await phase_3_fn(
            config,
            modules,
            file_to_module,
            phase1_results,
            target,
            output_dir=output_dir,
            verbose=verbose,
        )
        log_phase_done("Phase 3", started)
        if phase == 3:
            return None

    if verbose:
        print("Phase 4: Merging index ...")
    started = time.perf_counter()
    index = phase_4_merge_fn(
        phase0_data=phase0_data,
        phase1_results=phase1_results,
        modules=modules,
        file_to_module=file_to_module,
        project_node=project_node,
        target=target,
    )
    log_phase_done("Phase 4", started)

    out_path = output_dir / INDEX_FILE
    write_json(out_path, index)

    if verbose:
        stats = index["stats"]
        print(
            f"Index written: {stats['total_files']} files, "
            f"{stats['total_modules']} modules, "
            f"{stats['total_signatures']} signatures"
        )

    await cleanup_fn()
    return index
