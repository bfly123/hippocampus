"""hippo_expand — drill into a specific module or file path.

Supports two levels:
  L2: File list with descriptions for a module
  L3: Full signature details for files in a module/path

Path formats:
  mod:<module_id>   — expand a module by its ID
  <path_prefix>     — expand all files matching a path prefix

Usage:
  result = build_expand(index, "mod:core-engine", level="L3", budget=2000)
  print(result["content"])
"""

from __future__ import annotations

from typing import Any

from ..utils import estimate_tokens


def _resolve_files(
    index: dict[str, Any],
    path: str,
) -> tuple[str, list[tuple[str, dict]]]:
    """Resolve path to a list of (filepath, file_data) pairs.

    Returns (resolved_label, file_list).
    """
    files = index.get("files", {})

    if path.startswith("mod:"):
        module_id = path[4:]
        matched = [
            (fp, fd) for fp, fd in files.items()
            if fd.get("module") == module_id
        ]
        return module_id, matched

    # Path prefix match
    matched = [
        (fp, fd) for fp, fd in files.items()
        if fp.startswith(path)
    ]
    return path, matched


def _render_l2(label: str, file_list: list[tuple[str, dict]]) -> str:
    """Render L2: file list with descriptions."""
    file_list.sort(key=lambda x: x[0])
    lines = [f"## {label}", ""]
    for fp, fd in file_list:
        desc = fd.get("desc", "")
        tags = fd.get("tags", [])
        sig_count = len(fd.get("signatures", []))
        tag_str = f" [{', '.join(tags)}]" if tags else ""
        sig_str = f" ({sig_count} sigs)" if sig_count else ""
        lines.append(f"- `{fp}`{sig_str}{tag_str}: {desc}")
    lines.append("")
    return "\n".join(lines)


def _render_l3(label: str, file_list: list[tuple[str, dict]]) -> str:
    """Render L3: file details with full signature info."""
    file_list.sort(key=lambda x: x[0])
    lines = [f"## {label} (signatures)", ""]
    for fp, fd in file_list:
        desc = fd.get("desc", "")
        lang = fd.get("lang", "")
        lines.append(f"### `{fp}` ({lang})")
        lines.append("")
        if desc:
            lines.append(desc)
            lines.append("")
        sigs = fd.get("signatures", [])
        if sigs:
            for s in sigs:
                kind = s.get("kind", "")
                name = s.get("name", "")
                line_num = s.get("line", "")
                parent = s.get("parent", "")
                sdesc = s.get("desc", "")
                parent_str = f" (in {parent})" if parent else ""
                lines.append(
                    f"- `{name}` [{kind}, L{line_num}]{parent_str}: {sdesc}"
                )
            lines.append("")
        else:
            lines.append("_(no signatures)_")
            lines.append("")
    return "\n".join(lines)


def build_expand(
    index: dict[str, Any],
    path: str,
    level: str = "L2",
    budget: int = 2000,
) -> dict[str, Any]:
    """Build a budget-aware expansion of a module or path.

    Args:
        index: The hippocampus index dict.
        path: "mod:<id>" or a file path prefix.
        level: "L2" for file list, "L3" for signatures.
        budget: Token budget.

    Returns dict with:
        path: str             — resolved path/label
        consumed_tokens: int  — estimated tokens used
        level: str            — actual level rendered
        content: str          — Markdown text
    """
    label, file_list = _resolve_files(index, path)

    if not file_list:
        content = f"No files found matching `{path}`.\n"
        return {
            "path": path,
            "consumed_tokens": estimate_tokens(content),
            "level": level,
            "content": content,
        }

    if level == "L3":
        full_text = _render_l3(label, file_list)
    else:
        full_text = _render_l2(label, file_list)

    tokens = estimate_tokens(full_text)

    # If within budget, return as-is
    if tokens <= budget:
        return {
            "path": label,
            "consumed_tokens": tokens,
            "level": level,
            "content": full_text,
        }

    # Over budget: for L3, fall back to L2 if L3 is too large
    if level == "L3":
        l2_text = _render_l2(label, file_list)
        l2_tokens = estimate_tokens(l2_text)
        if l2_tokens <= budget:
            return {
                "path": label,
                "consumed_tokens": l2_tokens,
                "level": "L2",
                "content": l2_text
                    + "\n_(L3 exceeded budget, showing L2)_\n",
            }

    # Hard truncate by character budget
    from ..constants import CHARS_PER_TOKEN
    char_budget = budget * CHARS_PER_TOKEN
    truncated = full_text[:char_budget]
    truncated += "\n\n_(truncated to fit budget)_\n"

    return {
        "path": label,
        "consumed_tokens": budget,
        "level": level,
        "content": truncated,
    }
