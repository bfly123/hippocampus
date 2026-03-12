from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

TAG_HEADER = f"{'Rank':<6} {'File':<40} {'Line':<6} {'Symbol':<30} {'Kind':<10}"
TAG_RULE = "-" * 100


def format_ranked_tag_line(rank: int, tag: Sequence[object]) -> str:
    """Format one ranked tag item for CLI output."""
    if len(tag) == 5:
        rel_fname, _fname, line, name, kind = tag
        return f"{rank:<6} {rel_fname:<40} {line:<6} {name:<30} {kind:<10}"
    if len(tag) == 1:
        rel_fname = tag[0]
        return f"{rank:<6} {rel_fname:<40} {'N/A':<6} {'(no symbols)':<30} {'N/A':<10}"
    return f"{rank:<6} {str(tuple(tag)):<90}"


def build_ranked_tag_report(
    ranked_tags: Sequence[Sequence[object]],
    limit: int,
    file_count: int,
) -> list[str]:
    """Build full ranked tag report lines, including header and summary."""
    lines = [f"", f"Symbol ranking for {file_count} file(s):", TAG_HEADER, TAG_RULE]
    for rank, tag in enumerate(ranked_tags[:limit], 1):
        lines.append(format_ranked_tag_line(rank, tag))
    if len(ranked_tags) > limit:
        lines.append(f"")
        lines.append(f"... and {len(ranked_tags) - limit} more symbols")
    lines.append(f"")
    lines.append(f"Total symbols: {len(ranked_tags)}")
    return lines


def run_pipeline_steps(
    *,
    ctx: Any,
    quiet: bool,
    steps: Sequence[tuple[str, Callable[..., Any], Mapping[str, Any]]],
    echo: Callable[[str], Any],
) -> None:
    """Run click pipeline steps in order with consistent step banners."""
    for label, command, kwargs in steps:
        if not quiet:
            echo(f"=== {label} ===")
        ctx.invoke(command, **dict(kwargs))

    if not quiet:
        echo("=== Pipeline complete ===")
