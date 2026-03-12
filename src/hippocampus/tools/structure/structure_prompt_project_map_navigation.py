from __future__ import annotations

from typing import Any


def append_navigation_step(
    steps: list[str],
    seen_targets: set[str],
    *,
    target: str | None,
    text: str,
) -> bool:
    if not target or target in seen_targets:
        return False
    steps.append(text)
    seen_targets.add(target)
    return True


def navigation_steps(
    boundaries: list[dict[str, Any]],
    entry_files: list[tuple[str, str, float]],
    areas: list[tuple[str, int]],
) -> list[str]:
    steps: list[str] = []
    seen_targets: set[str] = set()
    _add_boundary_entry_steps(steps, seen_targets, boundaries)
    _add_boundary_area_steps(steps, seen_targets, boundaries)
    if not steps:
        _add_entry_steps(steps, seen_targets, entry_files)
    _add_area_steps(steps, seen_targets, areas)
    if not steps:
        steps.append(
            "Start with the highest-core module in the Modules section, then drill into its top key file."
        )
    return steps[:5]


def _add_boundary_entry_steps(
    steps: list[str],
    seen_targets: set[str],
    boundaries: list[dict[str, Any]],
) -> None:
    for item in boundaries[:2]:
        append_navigation_step(
            steps,
            seen_targets,
            target=item.get("entry"),
            text=f"Read `{item['entry']}` to understand `{item['project']}` runtime entry.",
        )


def _add_boundary_area_steps(
    steps: list[str],
    seen_targets: set[str],
    boundaries: list[dict[str, Any]],
) -> None:
    for item in boundaries[:2]:
        core_areas = item.get("core_areas") or []
        append_navigation_step(
            steps,
            seen_targets,
            target=core_areas[0] if core_areas else None,
            text=f"Expand `{core_areas[0] if core_areas else None}` for core implementation details.",
        )


def _add_entry_steps(
    steps: list[str],
    seen_targets: set[str],
    entry_files: list[tuple[str, str, float]],
) -> None:
    for file_path, reason, _score in entry_files[:2]:
        append_navigation_step(
            steps,
            seen_targets,
            target=file_path,
            text=f"Read `{file_path}` ({reason}) for initial orientation.",
        )


def _add_area_steps(
    steps: list[str],
    seen_targets: set[str],
    areas: list[tuple[str, int]],
) -> None:
    for area, count in areas[:2]:
        added = append_navigation_step(
            steps,
            seen_targets,
            target=area,
            text=f"Expand `{area}` for dense implementation coverage (~{count} source files).",
        )
        if added and len(steps) >= 3:
            break
