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
    max_inflight: int | None = None,
) -> None:
    total = len(files)
    if total == 0:
        return

    if verbose or show_progress:
        print(format_progress_line("Phase 1 progress", 0, total, detail="started"))

    completed = 0
    queue: asyncio.Queue[str] = asyncio.Queue()
    for path in files:
        queue.put_nowait(path)

    worker_count = min(total, max(1, int(max_inflight or total)))

    async def worker() -> None:
        nonlocal completed
        while True:
            try:
                path = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                await process_file(path)
            finally:
                completed += 1
                if (verbose or show_progress) and (
                    completed == total or completed % max(1, progress_every) == 0
                ):
                    print(format_progress_line("Phase 1 progress", completed, total))
                queue.task_done()

    tasks = [asyncio.create_task(worker()) for _ in range(worker_count)]
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


__all__ = ["run_phase1_processors"]
