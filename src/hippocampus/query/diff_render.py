"""Render helpers for index diff output."""

from __future__ import annotations

from typing import Any


def render_tag_change(item: dict[str, Any]) -> str:
    parts = []
    if item["added"]:
        parts.append(f"+[{', '.join(item['added'])}]")
    if item["removed"]:
        parts.append(f"-[{', '.join(item['removed'])}]")
    return f"- **tags** `{item['path']}`: {' '.join(parts)}"


def append_stats_section(lines: list[str], stats_diff: dict[str, int]) -> None:
    lines.extend(["## Stats Changes", ""])
    for key in ("files", "modules", "signatures"):
        value = stats_diff[key]
        sign = "+" if value > 0 else ""
        lines.append(f"- **{key}**: {sign}{value}")
    lines.append("")


def append_module_section(lines: list[str], diff_result: dict[str, Any]) -> None:
    added = diff_result["modules_added"]
    removed = diff_result["modules_removed"]
    changed = diff_result["modules_changed"]
    if not (added or removed or changed):
        return
    lines.extend(["## Module Changes", ""])
    for item in added:
        lines.append(f"- **+ {item['id']}**: {item['desc']}")
    for item in removed:
        lines.append(f"- **- {item['id']}**: {item['desc']}")
    for item in changed:
        lines.append(
            f"- **~ {item['old_id']}** → **{item['new_id']}** "
            f"(jaccard={item['jaccard']:.3f})"
        )
    lines.append("")


def append_file_section(lines: list[str], diff_result: dict[str, Any]) -> None:
    added = diff_result["files_added"]
    removed = diff_result["files_removed"]
    moved = diff_result["files_moved"]
    tag_changed = diff_result["files_tag_changed"]
    if not (added or removed or moved or tag_changed):
        return
    lines.extend(["## File Changes", ""])
    for path in added:
        lines.append(f"- **+** `{path}`")
    for path in removed:
        lines.append(f"- **-** `{path}`")
    for item in moved:
        lines.append(
            f"- **moved** `{item['path']}`: "
            f"{item['old_module']} → {item['new_module']}"
        )
    for item in tag_changed:
        lines.append(render_tag_change(item))
    lines.append("")
