from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable

from ..constants import INDEX_FILE, TREE_FILE
from ..llm.transport import close_http_clients
from ..types import TreeNode
from ..utils import read_json, write_json


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
        phase0_data = await phase_0_fn(target, output_dir, verbose)
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
        phase1_results = await phase_1_fn(
            config,
            phase0_data,
            target,
            output_dir=output_dir,
            dir_tree=dir_tree,
            verbose=verbose,
        )
        if phase == 1:
            return None

    modules = None
    file_to_module = None
    if phase is None or phase >= 2:
        if verbose:
            print("Phase 2: Module clustering ...")
        modules, file_to_module = await phase_2_fn(
            config,
            phase1_results,
            output_dir=output_dir,
            verbose=verbose,
        )
        if phase == 2:
            return None

    project_node = None
    if phase is None or phase >= 3:
        if verbose:
            print("Phase 3: Module descriptions + project overview ...")
        modules, project_node = await phase_3_fn(
            config,
            modules,
            file_to_module,
            phase1_results,
            target,
            output_dir=output_dir,
            verbose=verbose,
        )
        if phase == 3:
            return None

    if verbose:
        print("Phase 4: Merging index ...")
    index = phase_4_merge_fn(
        phase0_data=phase0_data,
        phase1_results=phase1_results,
        modules=modules,
        file_to_module=file_to_module,
        project_node=project_node,
        target=target,
    )

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
