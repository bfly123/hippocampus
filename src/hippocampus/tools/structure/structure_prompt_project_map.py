from __future__ import annotations

from typing import Any, Callable

from ...types import TreeNode
from .structure_prompt_project_map_boundaries import (
    collect_project_boundaries,
    rank_code_areas,
)
from .structure_prompt_project_map_navigation import navigation_steps
from .structure_prompt_project_map_brief import (
    generate_llm_navigation_brief,
    render_llm_navigation_brief_profile,
    run_async_brief,
    sanitize_navigation_brief_profile,
)
from .structure_prompt_project_map_paths import (
    infer_entry_reason,
    normalized_parts,
    rank_entry_files,
    split_path,
)
from .structure_strategy import describe_workspace_dir, entry_file_reasons_for_archetype


def _append_runtime_architecture(lines: list[str], architecture: str) -> None:
    if architecture:
        lines.extend(["### Runtime Architecture", "", architecture, ""])


def _workspace_dirs(
    root: TreeNode,
    *,
    skip_dir_fn: Callable[[str, tuple[str, ...]], bool],
) -> list[TreeNode]:
    top_dirs = [child for child in root.children if child.type == "dir" and not skip_dir_fn(child.name, ())]
    top_dirs.sort(key=lambda child: child.name.lower())
    return top_dirs


def _append_workspace_layout(
    lines: list[str],
    root: TreeNode,
    *,
    archetype: str,
    top_dirs_cap: int,
    skip_dir_fn: Callable[[str, tuple[str, ...]], bool],
) -> None:
    top_dirs = _workspace_dirs(root, skip_dir_fn=skip_dir_fn)
    if not top_dirs:
        return
    lines.extend(["### Workspace Layout", ""])
    for node in top_dirs[:top_dirs_cap]:
        lines.append(f"- `{node.name}/`: {describe_workspace_dir(node.name, archetype)}")
    if len(top_dirs) > top_dirs_cap:
        lines.append(f"- `...`: +{len(top_dirs) - top_dirs_cap} additional workspace directories")
    lines.append("")


def _append_entry_points(
    lines: list[str],
    entry_files: list[tuple[str, str, float]],
    *,
    entry_cap: int,
) -> None:
    if not entry_files:
        return
    lines.extend(["### Entry Points", ""])
    for file_path, reason, _score in entry_files[:entry_cap]:
        lines.append(f"- `{file_path}`: {reason}")
    if len(entry_files) > entry_cap:
        lines.append(f"- `...`: +{len(entry_files) - entry_cap} more entry candidates")
    lines.append("")

def _append_project_boundaries(lines: list[str], boundaries: list[dict[str, Any]], cap: int) -> None:
    if not boundaries:
        return
    lines.extend(["### Project Boundaries", ""])
    for item in boundaries[:cap]:
        core_hint = ", ".join(item["core_areas"]) if item["core_areas"] else "n/a"
        entry_hint = item["entry"] or "n/a"
        lines.append(
            f"- `{item['project']}/`: {item['source_files']} source files, "
            f"{item['test_files']} tests; entry `{entry_hint}`; core `{core_hint}`"
        )
    if len(boundaries) > cap:
        lines.append(f"- `...`: +{len(boundaries) - cap} additional project boundaries")
    lines.append("")


def _append_fast_navigation(
    lines: list[str],
    boundaries: list[dict[str, Any]],
    entry_files: list[tuple[str, str, float]],
    areas: list[tuple[str, int]],
) -> None:
    if not (boundaries or entry_files or areas):
        return
    lines.extend(["### Fast Navigation Path", ""])
    for idx, text in enumerate(navigation_steps(boundaries, entry_files, areas), start=1):
        lines.append(f"{idx}. {text}")
    lines.append("")


def _append_core_areas(lines: list[str], areas: list[tuple[str, int]]) -> None:
    if not areas:
        return
    lines.extend(["### Core Code Areas", ""])
    for area, count in areas:
        lines.append(f"- `{area}`: ~{count} source files")
    lines.append("")


def render_project_map(
    project: dict[str, Any],
    root: TreeNode,
    files: dict[str, dict],
    file_roles: dict[str, str],
    *,
    archetype: str,
    profile: dict[str, Any],
    skip_dir_fn: Callable[[str, tuple[str, ...]], bool],
) -> str:
    entry_cap = max(4, int(profile["llm_reading_items"]) + 2)
    top_dirs_cap = 10 if profile["name"] != "small" else 6
    boundary_cap = 6 if profile["name"] != "small" else 3
    entry_files = rank_entry_files(files, entry_file_reasons_for_archetype(archetype))
    boundaries = collect_project_boundaries(files, file_roles, entry_files)
    areas = rank_code_areas(files, file_roles)

    lines = ["## Project Map", ""]
    _append_runtime_architecture(lines, str(project.get("architecture", "")))
    _append_workspace_layout(
        lines,
        root,
        archetype=archetype,
        top_dirs_cap=top_dirs_cap,
        skip_dir_fn=skip_dir_fn,
    )
    _append_entry_points(lines, entry_files, entry_cap=entry_cap)
    _append_project_boundaries(lines, boundaries, boundary_cap)
    _append_fast_navigation(lines, boundaries, entry_files, areas)
    _append_core_areas(lines, areas)
    return "\n".join(lines)


__all__ = [
    "collect_project_boundaries",
    "generate_llm_navigation_brief",
    "infer_entry_reason",
    "normalized_parts",
    "rank_code_areas",
    "rank_entry_files",
    "render_llm_navigation_brief_profile",
    "render_project_map",
    "run_async_brief",
    "sanitize_navigation_brief_profile",
    "split_path",
]
