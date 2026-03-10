from __future__ import annotations

from typing import Any

from .structure_prompt_navigation import (
    build_known_paths,
    build_navigation_brief_prompt,
    parse_json_block,
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
    from ..llm.client import HippoLLM

    reading_cap = int(profile["llm_reading_items"])
    axes_cap = int(profile["llm_axes_items"])
    hotspots_cap = int(profile["llm_hotspots_items"])
    entry_files = rank_entry_files(files, entry_file_reasons_for_archetype(archetype))
    boundaries = collect_project_boundaries(files, file_roles, entry_files)
    areas = rank_code_areas(files, file_roles)
    key_files = [(fp, fd) for fp, fd in files.items() if file_roles.get(fp) == "source"]
    key_files.sort(key=lambda item: float(item[1].get("score") or 0), reverse=True)
    known_paths = build_known_paths(files, split_path=split_path)

    module_rows = [
        {"id": mod.get("id", ""), "tier": mod.get("tier", ""), "core_score": mod.get("core_score", 0), "file_count": mod.get("file_count", 0), "desc": mod.get("desc", "")}
        for mod in modules[:14]
    ]
    context_payload = {
        "project": {"overview": project.get("overview", ""), "architecture": project.get("architecture", ""), "scale": project.get("scale", {}), "archetype": archetype},
        "entry_points": [{"path": p, "reason": r} for p, r, _ in entry_files[: max(6, reading_cap + 2)]],
        "project_boundaries": boundaries,
        "core_code_areas": [{"path": area, "source_files": count} for area, count in areas],
        "key_files": [{"path": fp, "desc": fd.get("desc", "")} for fp, fd in key_files[:24]],
        "modules": module_rows,
    }
    candidate_paths = (
        {e["path"] for e in context_payload["entry_points"]}
        | {i["path"] for i in context_payload["key_files"]}
        | {i["path"] for i in context_payload["core_code_areas"]}
        | {b["project"] + "/" for b in boundaries}
        | {b.get("entry", "") for b in boundaries if b.get("entry")}
    )
    prompt = build_navigation_brief_prompt(
        candidate_paths={path for path in candidate_paths if path},
        context_payload=context_payload,
        reading_cap=reading_cap,
        axes_cap=axes_cap,
        hotspots_cap=hotspots_cap,
    )
    llm = HippoLLM(config)
    validator = lambda text: validate_navigation_brief_json(text, known_paths)
    text, errors = await llm.call_with_retry("architect", [{"role": "user", "content": prompt}], validator=validator)
    if errors:
        return None
    data = parse_json_block(text)
    if data is None:
        return None
    return sanitize_navigation_brief(data, known_paths, reading_cap=reading_cap, axes_cap=axes_cap, hotspots_cap=hotspots_cap)


def sanitize_navigation_brief_profile(data: dict[str, Any], known_paths: set[str], profile: dict[str, Any]) -> dict[str, Any]:
    return sanitize_navigation_brief(
        data,
        known_paths,
        reading_cap=int(profile["llm_reading_items"]),
        axes_cap=int(profile["llm_axes_items"]),
        hotspots_cap=int(profile["llm_hotspots_items"]),
    )


def render_llm_navigation_brief_profile(brief: dict[str, Any], profile: dict[str, Any]) -> str:
    return render_llm_navigation_brief(
        brief,
        reading_cap=int(profile["llm_reading_items"]),
        axes_cap=int(profile["llm_axes_items"]),
        hotspots_cap=int(profile["llm_hotspots_items"]),
    )


def run_async_brief(coro):
    return run_async(coro)
