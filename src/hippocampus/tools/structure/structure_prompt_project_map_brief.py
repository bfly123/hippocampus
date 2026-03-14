from __future__ import annotations

from typing import Any

from ...llm.gateway import create_llm_gateway

from .structure_prompt_navigation import (
    build_known_paths,
    build_navigation_brief_prompt,
    render_llm_navigation_brief,
    run_async,
    sanitize_navigation_brief,
    validate_navigation_brief_json,
)
from .structure_prompt_project_map_boundaries import (
    collect_project_boundaries,
    rank_code_areas,
)
from .structure_prompt_project_map_paths import rank_entry_files, split_path
from .structure_strategy import entry_file_reasons_for_archetype


def _profile_caps(profile: dict[str, Any]) -> tuple[int, int, int]:
    return (
        int(profile["llm_reading_items"]),
        int(profile["llm_axes_items"]),
        int(profile["llm_hotspots_items"]),
    )


def _ranked_key_files(
    files: dict[str, dict],
    file_roles: dict[str, str],
) -> list[tuple[str, dict]]:
    ranked = [(path, data) for path, data in files.items() if file_roles.get(path) == "source"]
    ranked.sort(key=lambda item: float(item[1].get("score") or 0), reverse=True)
    return ranked


def _module_rows(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": module.get("id", ""),
            "tier": module.get("tier", ""),
            "core_score": module.get("core_score", 0),
            "file_count": module.get("file_count", 0),
            "desc": module.get("desc", ""),
        }
        for module in modules[:14]
    ]


def _build_context_payload(
    *,
    project: dict[str, Any],
    archetype: str,
    entry_files: list[tuple[str, str, float]],
    boundaries: list[dict[str, Any]],
    areas: list[tuple[str, int]],
    key_files: list[tuple[str, dict]],
    modules: list[dict[str, Any]],
    reading_cap: int,
) -> dict[str, Any]:
    return {
        "project": {
            "overview": project.get("overview", ""),
            "architecture": project.get("architecture", ""),
            "scale": project.get("scale", {}),
            "archetype": archetype,
        },
        "entry_points": [
            {"path": path, "reason": reason}
            for path, reason, _score in entry_files[: max(6, reading_cap + 2)]
        ],
        "project_boundaries": boundaries,
        "core_code_areas": [
            {"path": area, "source_files": count}
            for area, count in areas
        ],
        "key_files": [
            {"path": path, "desc": file_data.get("desc", "")}
            for path, file_data in key_files[:24]
        ],
        "modules": _module_rows(modules),
    }


def _candidate_paths(
    context_payload: dict[str, Any],
    boundaries: list[dict[str, Any]],
) -> set[str]:
    return {
        path
        for path in (
            {entry["path"] for entry in context_payload["entry_points"]}
            | {item["path"] for item in context_payload["key_files"]}
            | {item["path"] for item in context_payload["core_code_areas"]}
            | {f"{boundary['project']}/" for boundary in boundaries}
            | {boundary.get("entry", "") for boundary in boundaries if boundary.get("entry")}
        )
        if path
    }


async def generate_llm_navigation_brief(
    project: dict[str, Any],
    modules: list[dict[str, Any]],
    files: dict[str, dict],
    file_roles: dict[str, str],
    config,
    *,
    archetype: str,
    profile: dict[str, Any],
) -> dict[str, Any] | None:
    reading_cap, axes_cap, hotspots_cap = _profile_caps(profile)
    entry_files = rank_entry_files(files, entry_file_reasons_for_archetype(archetype))
    boundaries = collect_project_boundaries(files, file_roles, entry_files)
    context_payload = _build_context_payload(
        project=project,
        archetype=archetype,
        entry_files=entry_files,
        boundaries=boundaries,
        areas=rank_code_areas(files, file_roles),
        key_files=_ranked_key_files(files, file_roles),
        modules=modules,
        reading_cap=reading_cap,
    )
    known_paths = build_known_paths(files, split_path=split_path)
    prompt = build_navigation_brief_prompt(
        candidate_paths=_candidate_paths(context_payload, boundaries),
        context_payload=context_payload,
        reading_cap=reading_cap,
        axes_cap=axes_cap,
        hotspots_cap=hotspots_cap,
    )

    llm = create_llm_gateway(config)
    validator = lambda text: validate_navigation_brief_json(text, known_paths)
    result = await llm.run_json_task_with_retry(
        "architect",
        [{"role": "user", "content": prompt}],
        validator=validator,
    )
    if result.errors:
        return None

    data = result.data if isinstance(result.data, dict) else None
    if data is None:
        return None
    return sanitize_navigation_brief_profile(data, known_paths, profile)


def sanitize_navigation_brief_profile(
    data: dict[str, Any],
    known_paths: set[str],
    profile: dict[str, Any],
) -> dict[str, Any]:
    reading_cap, axes_cap, hotspots_cap = _profile_caps(profile)
    return sanitize_navigation_brief(
        data,
        known_paths,
        reading_cap=reading_cap,
        axes_cap=axes_cap,
        hotspots_cap=hotspots_cap,
    )


def render_llm_navigation_brief_profile(brief: dict[str, Any], profile: dict[str, Any]) -> str:
    reading_cap, axes_cap, hotspots_cap = _profile_caps(profile)
    return render_llm_navigation_brief(
        brief,
        reading_cap=reading_cap,
        axes_cap=axes_cap,
        hotspots_cap=hotspots_cap,
    )


def run_async_brief(coro):
    return run_async(coro)
