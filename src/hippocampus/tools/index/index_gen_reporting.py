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


__all__ = ["format_failed_file_summary", "format_phase_duration"]
