"""Index diff — compare two index versions and produce structured change summary."""

from __future__ import annotations

from typing import Any

from .diff_match import diff_files, match_modules
from .diff_render import append_file_section, append_module_section, append_stats_section
from ..utils import estimate_tokens


def _match_modules(
    old_mods: list[dict],
    old_files: dict[str, dict],
    new_mods: list[dict],
    new_files: dict[str, dict],
) -> dict:
    return match_modules(old_mods, old_files, new_mods, new_files)


def _diff_stats(old_index: dict, new_index: dict) -> dict:
    """Compute delta between stats fields."""
    old_s = old_index.get("stats", {})
    new_s = new_index.get("stats", {})
    return {
        "files": new_s.get("total_files", 0) - old_s.get("total_files", 0),
        "modules": new_s.get("total_modules", 0) - old_s.get("total_modules", 0),
        "signatures": (
            new_s.get("total_signatures", 0) - old_s.get("total_signatures", 0)
        ),
    }


def _diff_modules(old_index: dict, new_index: dict, module_match: dict) -> dict:
    """Compute module-level changes."""
    modules_added = [
        {"id": m["id"], "desc": m.get("desc", "")}
        for m in module_match["added"]
    ]
    modules_removed = [
        {"id": m["id"], "desc": m.get("desc", "")}
        for m in module_match["removed"]
    ]
    modules_changed = [
        {"old_id": om["id"], "new_id": nm["id"], "jaccard": round(j, 3)}
        for om, nm, j in module_match["matched"]
    ]
    return {
        "modules_added": modules_added,
        "modules_removed": modules_removed,
        "modules_changed": modules_changed,
    }


def _diff_files(old_index: dict, new_index: dict, module_match: dict | None = None) -> dict:
    return diff_files(old_index, new_index, module_match=module_match)
def _render_diff(diff_result: dict) -> str:
    """Render diff result as Markdown."""
    lines = ["# Index Diff", ""]
    append_stats_section(lines, diff_result["stats_diff"])
    append_module_section(lines, diff_result)
    append_file_section(lines, diff_result)

    mag = diff_result["change_magnitude"]
    lines.append(f"**Total change magnitude**: {mag}")
    lines.append("")

    return "\n".join(lines)


def build_diff(
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_id: str = "old",
    new_id: str = "new",
) -> dict[str, Any]:
    """Build a structured diff between two index versions.

    Returns dict with stats_diff, module/file changes, Markdown content.
    """
    old_files = old_index.get("files", {})
    new_files = new_index.get("files", {})
    old_mods = old_index.get("modules", [])
    new_mods = new_index.get("modules", [])

    module_match = match_modules(old_mods, old_files, new_mods, new_files)
    stats_diff = _diff_stats(old_index, new_index)
    mod_diff = _diff_modules(old_index, new_index, module_match)
    file_diff = diff_files(old_index, new_index, module_match=module_match)

    change_magnitude = (
        len(file_diff["files_added"])
        + len(file_diff["files_removed"])
        + len(file_diff["files_moved"])
        + len(file_diff["files_tag_changed"])
        + len(mod_diff["modules_added"])
        + len(mod_diff["modules_removed"])
    )

    result = {
        "old_id": old_id,
        "new_id": new_id,
        "stats_diff": stats_diff,
        **mod_diff,
        **file_diff,
        "change_magnitude": change_magnitude,
    }

    content = _render_diff(result)
    result["consumed_tokens"] = estimate_tokens(content)
    result["content"] = content

    return result
