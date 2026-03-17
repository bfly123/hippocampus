from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable

from llmgateway.transport import close_http_clients
from .index_gen_runtime_support import (
    load_dir_tree,
    local_only_index,
    merge_index,
    print_index_stats,
    run_phase_0,
    run_phase_1,
    run_phase_2,
    run_phase_3,
    write_index,
)


async def cleanup_llm_clients() -> None:
    """Close shared HTTP clients used by llmgateway transport."""
    try:
        await close_http_clients()
    except Exception:
        pass


def _should_run_phase(phase: int | None, phase_number: int) -> bool:
    return phase is None or phase >= phase_number


async def run_index_pipeline_impl(
    target: Path,
    output_dir: Path,
    phase: int | None,
    verbose: bool,
    show_progress: bool,
    no_llm: bool,
    phase_0_fn: Callable[[Path, Path, bool], Awaitable[dict[str, Any]]],
    phase_1_fn: Callable[..., Awaitable[dict[str, dict]]],
    phase_2_fn: Callable[..., Awaitable[tuple[list[dict], dict[str, str]]]],
    phase_3_fn: Callable[..., Awaitable[tuple[list[dict], dict]]],
    phase_4_merge_fn: Callable[..., dict],
    cleanup_fn: Callable[[], Awaitable[None]],
    config: Any,
) -> dict | None:
    dir_tree = load_dir_tree(output_dir)
    phase0_data = None
    if _should_run_phase(phase, 0):
        phase0_data = await run_phase_0(
            phase_0_fn,
            target=target,
            output_dir=output_dir,
            verbose=verbose,
            show_progress=show_progress,
        )
        if phase == 0:
            return None

    if no_llm:
        if verbose or show_progress:
            print("Local-only mode: skipping LLM phases ...")
        index = local_only_index(phase_4_merge_fn, phase0_data=phase0_data, target=target)
        write_index(output_dir, index)
        return index

    phase1_results = None
    if _should_run_phase(phase, 1):
        phase1_results = await run_phase_1(
            phase_1_fn,
            config=config,
            phase0_data=phase0_data,
            target=target,
            output_dir=output_dir,
            dir_tree=dir_tree,
            verbose=verbose,
            show_progress=show_progress,
        )
        if phase == 1:
            return None

    modules = None
    file_to_module = None
    if _should_run_phase(phase, 2):
        modules, file_to_module = await run_phase_2(
            phase_2_fn,
            config=config,
            phase1_results=phase1_results,
            output_dir=output_dir,
            verbose=verbose,
            show_progress=show_progress,
        )
        if phase == 2:
            return None

    project_node = None
    if _should_run_phase(phase, 3):
        modules, project_node = await run_phase_3(
            phase_3_fn,
            config=config,
            modules=modules,
            file_to_module=file_to_module,
            phase1_results=phase1_results,
            target=target,
            output_dir=output_dir,
            verbose=verbose,
            show_progress=show_progress,
        )
        if phase == 3:
            return None

    index = merge_index(
        phase_4_merge_fn,
        phase0_data=phase0_data,
        phase1_results=phase1_results,
        modules=modules,
        file_to_module=file_to_module,
        project_node=project_node,
        target=target,
        verbose=verbose,
        show_progress=show_progress,
    )
    write_index(output_dir, index)
    print_index_stats(index, verbose=verbose, show_progress=show_progress)
    await cleanup_fn()
    return index
