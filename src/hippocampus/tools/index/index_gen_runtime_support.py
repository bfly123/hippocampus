from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from ...constants import INDEX_FILE, TREE_FILE
from ...types import TreeNode
from ...utils import read_json, write_json
from .index_gen_reporting import format_phase_duration


def log_phase_done(label: str, start_time: float, *, verbose: bool) -> None:
    if verbose:
        duration = format_phase_duration(time.perf_counter() - start_time)
        print(f"{label} done in {duration}")


def load_dir_tree(output_dir: Path) -> str:
    tree_path = output_dir / TREE_FILE
    if not tree_path.exists():
        return ""
    tree_data = read_json(tree_path)
    from ..structure.structure_prompt import _render_node

    root = TreeNode(**tree_data["root"])
    return _render_node(root)


def write_index(output_dir: Path, index: dict) -> None:
    write_json(output_dir / INDEX_FILE, index)


async def run_phase(
    label: str,
    *,
    verbose: bool,
    runner: Callable[[], Awaitable[Any]],
):
    if verbose:
        print(f"{label} ...")
    started = time.perf_counter()
    result = await runner()
    log_phase_done(label.split(":", 1)[0], started, verbose=verbose)
    return result


def local_only_index(phase_4_merge_fn, *, phase0_data, target: Path) -> dict:
    return phase_4_merge_fn(
        phase0_data=phase0_data,
        phase1_results={},
        modules=[],
        file_to_module={},
        project_node={},
        target=target,
        local_only=True,
    )


async def run_phase_0(phase_0_fn, *, target: Path, output_dir: Path, verbose: bool):
    return await run_phase(
        "Phase 0: Local extraction",
        verbose=verbose,
        runner=lambda: phase_0_fn(target, output_dir, verbose),
    )


async def run_phase_1(
    phase_1_fn,
    *,
    config: Any,
    phase0_data,
    target: Path,
    output_dir: Path,
    dir_tree: str,
    verbose: bool,
):
    return await run_phase(
        "Phase 1: Per-file LLM analysis",
        verbose=verbose,
        runner=lambda: phase_1_fn(
            config,
            phase0_data,
            target,
            output_dir=output_dir,
            dir_tree=dir_tree,
            verbose=verbose,
        ),
    )


async def run_phase_2(
    phase_2_fn,
    *,
    config: Any,
    phase1_results,
    output_dir: Path,
    verbose: bool,
):
    return await run_phase(
        "Phase 2: Module clustering",
        verbose=verbose,
        runner=lambda: phase_2_fn(
            config,
            phase1_results,
            output_dir=output_dir,
            verbose=verbose,
        ),
    )


async def run_phase_3(
    phase_3_fn,
    *,
    config: Any,
    modules,
    file_to_module,
    phase1_results,
    target: Path,
    output_dir: Path,
    verbose: bool,
):
    return await run_phase(
        "Phase 3: Module descriptions + project overview",
        verbose=verbose,
        runner=lambda: phase_3_fn(
            config,
            modules,
            file_to_module,
            phase1_results,
            target,
            output_dir=output_dir,
            verbose=verbose,
        ),
    )


def merge_index(
    phase_4_merge_fn,
    *,
    phase0_data,
    phase1_results,
    modules,
    file_to_module,
    project_node,
    target: Path,
    verbose: bool,
) -> dict:
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
    log_phase_done("Phase 4", started, verbose=verbose)
    return index


def print_index_stats(index: dict, *, verbose: bool) -> None:
    if not verbose:
        return
    stats = index["stats"]
    print(
        f"Index written: {stats['total_files']} files, "
        f"{stats['total_modules']} modules, "
        f"{stats['total_signatures']} signatures"
    )
