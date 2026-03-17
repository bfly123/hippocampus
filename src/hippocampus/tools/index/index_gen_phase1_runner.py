from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from .index_gen_reporting import format_progress_line


Phase1Processor = Callable[[str], Awaitable[None]]


async def run_phase1_processors(
    files: list[str],
    *,
    process_file: Phase1Processor,
    verbose: bool,
    show_progress: bool = False,
    progress_every: int = 10,
) -> None:
    total = len(files)
    if total == 0:
        return

    if verbose or show_progress:
        print(format_progress_line("Phase 1 progress", 0, total, detail="started"))

    completed = 0
    tasks = [asyncio.create_task(process_file(path)) for path in files]
    try:
        for task in asyncio.as_completed(tasks):
            await task
            completed += 1
            if (verbose or show_progress) and (completed == total or completed % max(1, progress_every) == 0):
                print(format_progress_line("Phase 1 progress", completed, total))
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


__all__ = ["run_phase1_processors"]
