"""Tree rendering helpers for structure prompt."""

from __future__ import annotations

from typing import Any

from ...types import TreeNode
from .structure_prompt_tree_filters import (
    normalized_parts,
    skip_dir,
    skip_file,
)


def _profile_limits(profile: dict[str, Any]) -> tuple[int, int, int]:
    return (
        int(profile.get("files_per_dir", 10)),
        int(profile.get("dirs_per_dir", 12)),
        int(profile.get("tree_depth", 4)),
    )


def _visible_children(
    node: TreeNode,
    current_parts: tuple[str, ...],
) -> tuple[list[TreeNode], list[TreeNode]]:
    files = [
        child
        for child in node.children
        if child.type == "file" and not skip_file(child.name, current_parts)
    ]
    dirs = [
        child
        for child in node.children
        if child.type == "dir" and not skip_dir(child.name, current_parts)
    ]
    files.sort(key=lambda child: child.name.lower())
    dirs.sort(key=lambda child: child.name.lower())
    return files, dirs


def _append_file_listing(out: list[str], prefix: str, files: list[TreeNode], limit: int) -> None:
    for child in files[:limit]:
        out.append(f"{prefix}  {child.name}\n")
    extra = len(files) - limit
    if extra > 0:
        out.append(f"{prefix}  ... (+{extra} more files)\n")


def _append_dir_listing(
    out: list[str],
    prefix: str,
    dirs: list[TreeNode],
    current_parts: tuple[str, ...],
    depth: int,
    profile: dict[str, Any],
    limit: int,
) -> None:
    for child in dirs[:limit]:
        out.append(render_node(child, depth + 1, current_parts, profile))
    extra = len(dirs) - limit
    if extra > 0:
        out.append(f"{prefix}  ... (+{extra} more dirs)\n")


def render_node(
    node: TreeNode,
    depth: int = 0,
    parent_parts: tuple[str, ...] = (),
    profile: dict[str, Any] | None = None,
) -> str:
    profile = profile or {}
    files_per_dir, dirs_per_dir, tree_depth = _profile_limits(profile)

    prefix = "  " * depth
    if node.type == "file":
        return f"{prefix}{node.name}\n"
    if skip_dir(node.name, parent_parts):
        return ""

    current_parts = normalized_parts(parent_parts + (() if node.name == "." else (node.name,)))
    files, dirs = _visible_children(node, current_parts)
    out: list[str] = [f"{prefix}{node.name}/\n"]
    if depth >= tree_depth:
        out.append(f"{prefix}  ... ({len(files)} files, {len(dirs)} dirs)\n")
        return "".join(out)

    _append_file_listing(out, prefix, files, files_per_dir)
    _append_dir_listing(out, prefix, dirs, current_parts, depth, profile, dirs_per_dir)
    return "".join(out)


def _summarize_child_dir(child: TreeNode) -> str:
    child_dirs = [
        item
        for item in child.children
        if item.type == "dir" and not skip_dir(item.name, (child.name,))
    ]
    child_files = [
        item
        for item in child.children
        if item.type == "file" and not skip_file(item.name, (child.name,))
    ]
    return f"  {child.name}/ ({len(child_files)} files, {len(child_dirs)} dirs)"


def _visible_top_level_children(node: TreeNode) -> tuple[list[TreeNode], list[TreeNode]]:
    visible_dirs = sorted(
        [child for child in node.children if child.type == "dir" and not skip_dir(child.name, ())],
        key=lambda child: child.name.lower(),
    )
    visible_files = sorted(
        [child for child in node.children if child.type == "file" and not skip_file(child.name, ())],
        key=lambda child: child.name.lower(),
    )
    return visible_dirs, visible_files


def _truncated_tree_lines(
    node: TreeNode,
    *,
    files_per_dir: int,
    top_summary_dirs: int,
) -> list[str]:
    lines = ["./"]
    visible_dirs, visible_files = _visible_top_level_children(node)
    lines.extend(f"  {child.name}" for child in visible_files[:files_per_dir])
    lines.extend(_summarize_child_dir(child) for child in visible_dirs[:top_summary_dirs])
    extra_dirs = len(visible_dirs) - top_summary_dirs
    if extra_dirs > 0:
        lines.append(f"  ... (+{extra_dirs} more top-level dirs)")
    return lines


def truncate_tree(
    node: TreeNode,
    max_chars: int,
    profile: dict[str, Any] | None = None,
) -> str:
    profile = profile or {}
    files_per_dir = int(profile.get("files_per_dir", 10))
    top_summary_dirs = int(profile.get("top_summary_dirs", 18))

    full = render_node(node, profile=profile)
    if len(full) <= max_chars:
        return full

    return "\n".join(
        _truncated_tree_lines(
            node,
            files_per_dir=files_per_dir,
            top_summary_dirs=top_summary_dirs,
        )
    ) + "\n"
