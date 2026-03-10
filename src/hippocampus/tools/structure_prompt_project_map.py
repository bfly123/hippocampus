from __future__ import annotations

from typing import Any, Callable

from ..types import TreeNode
from .structure_prompt_project_map_boundaries import (
    collect_project_boundaries,
    rank_code_areas,
)
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
    entry_reasons = entry_file_reasons_for_archetype(archetype)

    lines = ["## Project Map", ""]
    arch = project.get("architecture", "")
    if arch:
        lines.extend(["### Runtime Architecture", "", arch, ""])

    top_dirs = [c for c in root.children if c.type == "dir" and not skip_dir_fn(c.name, ())]
    top_dirs.sort(key=lambda c: c.name.lower())
    if top_dirs:
        lines.extend(["### Workspace Layout", ""])
        for node in top_dirs[:top_dirs_cap]:
            lines.append(f"- `{node.name}/`: {describe_workspace_dir(node.name, archetype)}")
        if len(top_dirs) > top_dirs_cap:
            lines.append(f"- `...`: +{len(top_dirs) - top_dirs_cap} additional workspace directories")
        lines.append("")

    entry_files = rank_entry_files(files, entry_reasons)
    if entry_files:
        lines.extend(["### Entry Points", ""])
        for fp, reason, _score in entry_files[:entry_cap]:
            lines.append(f"- `{fp}`: {reason}")
        if len(entry_files) > entry_cap:
            lines.append(f"- `...`: +{len(entry_files) - entry_cap} more entry candidates")
        lines.append("")

    boundaries = collect_project_boundaries(files, file_roles, entry_files)
    areas = rank_code_areas(files, file_roles)
    _append_project_boundaries(lines, boundaries, boundary_cap)
    _append_fast_navigation(lines, boundaries, entry_files, areas)
    _append_core_areas(lines, areas)
    return "\n".join(lines)


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
    steps: list[str] = []
    seen_targets: set[str] = set()
    for item in boundaries[:2]:
        if item["entry"] and item["entry"] not in seen_targets:
            steps.append(f"Read `{item['entry']}` to understand `{item['project']}` runtime entry.")
            seen_targets.add(item["entry"])
    for item in boundaries[:2]:
        if item["core_areas"]:
            target = item["core_areas"][0]
            if target not in seen_targets:
                steps.append(f"Expand `{target}` for core implementation details.")
                seen_targets.add(target)
    if not steps:
        for fp, reason, _score in entry_files[:2]:
            if fp not in seen_targets:
                steps.append(f"Read `{fp}` ({reason}) for initial orientation.")
                seen_targets.add(fp)
    if len(steps) < 3:
        for area, count in areas[:2]:
            if area not in seen_targets:
                steps.append(f"Expand `{area}` for dense implementation coverage (~{count} source files).")
                seen_targets.add(area)
            if len(steps) >= 3:
                break
    if not steps:
        steps.append("Start with the highest-core module in the Modules section, then drill into its top key file.")
    for idx, text in enumerate(steps[:5], start=1):
        lines.append(f"{idx}. {text}")
    lines.append("")


def _append_core_areas(lines: list[str], areas: list[tuple[str, int]]) -> None:
    if not areas:
        return
    lines.extend(["### Core Code Areas", ""])
    for area, count in areas:
        lines.append(f"- `{area}`: ~{count} source files")
    lines.append("")


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
