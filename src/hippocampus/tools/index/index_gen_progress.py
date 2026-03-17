from __future__ import annotations

import asyncio
import inspect
from typing import Sequence

from llmgateway import JSONResult, TaskRequest, Validator
from llmgateway.json import try_parse_json

from .index_gen_reporting import format_progress_line


async def run_json_requests_with_progress(
    *,
    llm,
    requests: Sequence[TaskRequest],
    validators: Sequence[Validator | None],
    verbose: bool,
    show_progress: bool,
    label: str,
    detail: str = "",
) -> list[JSONResult]:
    if len(requests) != len(validators):
        raise ValueError("validators length must match requests length")

    total = len(requests)
    if total == 0:
        return []

    if verbose or show_progress:
        runtime = getattr(llm, "runtime", None)
        concurrency = getattr(runtime, "max_concurrent", "?")
        suffix = f", {detail}" if detail else ""
        print(
            f"{label}: scheduled {total} request(s), "
            f"max_concurrent={concurrency}{suffix}"
        )
        print(format_progress_line(label, 0, total, detail="started"))

    service = getattr(llm, "service", None)
    generate_text_with_retry = getattr(service, "generate_text_with_retry", None)
    if (
        service is None
        or generate_text_with_retry is None
        or not inspect.iscoroutinefunction(generate_text_with_retry)
    ):
        results = list(await llm.run_json_tasks_with_retry(list(requests), list(validators)))
        if verbose or show_progress:
            print(format_progress_line(label, total, total, detail="completed"))
        return results

    async def worker(
        index: int,
        request: TaskRequest,
        validator: Validator | None,
    ) -> tuple[int, JSONResult]:
        text, errors = await generate_text_with_retry(request, validator)
        data, _error = try_parse_json(text)
        return index, JSONResult(
            task=request.task,
            text=text,
            data=data,
            errors=list(errors),
        )

    pending = [
        asyncio.create_task(worker(index, request, validator))
        for index, (request, validator) in enumerate(zip(requests, validators))
    ]
    ordered: list[JSONResult | None] = [None] * total
    completed = 0
    try:
        for task in asyncio.as_completed(pending):
            index, result = await task
            ordered[index] = result
            completed += 1
            if verbose or show_progress:
                print(format_progress_line(label, completed, total))
    finally:
        for task in pending:
            if not task.done():
                task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    return [result for result in ordered if result is not None]


__all__ = ["run_json_requests_with_progress"]
