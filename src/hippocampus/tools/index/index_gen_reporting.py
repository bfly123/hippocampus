from __future__ import annotations

from typing import Iterable


def format_phase_duration(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return f"{minutes}m{remainder:04.1f}s"


def format_failed_file_summary(
    failed: Iterable[str],
    *,
    total_processed: int,
    preview_limit: int = 10,
) -> str:
    failed_list = list(failed)
    count = len(failed_list)
    if count == 0:
        return "Phase 1 failed files: 0"
    preview = ", ".join(failed_list[:preview_limit])
    remaining = count - min(count, preview_limit)
    suffix = f", ... +{remaining} more" if remaining > 0 else ""
    return (
        f"Phase 1 failed files: {count}/{total_processed} "
        f"({preview}{suffix})"
    )


def format_progress_bar(
    completed: int,
    total: int,
    *,
    width: int = 24,
) -> str:
    total = max(0, int(total))
    completed = min(max(0, int(completed)), total) if total else 0
    if total <= 0:
        return "[" + "." * max(8, int(width)) + "]"
    width = max(8, int(width))
    filled = min(width, int(round((completed / total) * width)))
    return "[" + "#" * filled + "." * (width - filled) + "]"


def format_progress_line(
    label: str,
    completed: int,
    total: int,
    *,
    detail: str = "",
    width: int = 24,
) -> str:
    normalized_total = max(0, int(total))
    normalized_completed = (
        min(max(0, int(completed)), normalized_total)
        if normalized_total
        else 0
    )
    ratio = (
        (normalized_completed / normalized_total) * 100
        if normalized_total > 0
        else 0.0
    )
    suffix = f" | {detail}" if detail else ""
    return (
        f"{label}: "
        f"{format_progress_bar(normalized_completed, normalized_total, width=width)} "
        f"{normalized_completed}/{normalized_total} ({ratio:5.1f}%)"
        f"{suffix}"
    )


__all__ = [
    "format_failed_file_summary",
    "format_phase_duration",
    "format_progress_bar",
    "format_progress_line",
]
