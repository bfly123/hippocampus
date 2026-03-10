from __future__ import annotations

import asyncio
import json
from typing import Any, Callable


def parse_json_block(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def build_known_paths(
    files: dict[str, dict],
    *,
    split_path: Callable[[str], tuple[str, ...]],
) -> set[str]:
    known: set[str] = set(files.keys())
    for file_path in files:
        parts = split_path(file_path)
        prefix: list[str] = []
        for part in parts[:-1]:
            prefix.append(part)
            directory = "/".join(prefix)
            known.add(directory)
            known.add(f"{directory}/")
    return known


def is_known_path(path: str, known_paths: set[str]) -> bool:
    if path in known_paths:
        return True
    stripped = path.rstrip("/")
    return stripped in known_paths or f"{stripped}/" in known_paths


def validate_navigation_brief_json(text: str, known_paths: set[str]) -> list[str]:
    errors: list[str] = []
    data = parse_json_block(text)
    if data is None:
        return ["Output must be a JSON object."]

    if not isinstance(data.get("summary"), str) or not data["summary"].strip():
        errors.append("Missing non-empty 'summary'.")

    reading = data.get("reading_order")
    if not isinstance(reading, list):
        errors.append("'reading_order' must be a list.")
    else:
        for idx, item in enumerate(reading):
            if not isinstance(item, dict):
                errors.append(f"reading_order[{idx}] must be an object.")
                continue
            path = str(item.get("path", "")).strip()
            why = str(item.get("why", "")).strip()
            if not path:
                errors.append(f"reading_order[{idx}] missing path.")
            elif not is_known_path(path, known_paths):
                errors.append(f"reading_order[{idx}] path not in repository: {path}")
            if not why:
                errors.append(f"reading_order[{idx}] missing why.")

    axes = data.get("architecture_axes")
    if not isinstance(axes, list):
        errors.append("'architecture_axes' must be a list.")
    else:
        for idx, axis in enumerate(axes):
            if not isinstance(axis, str) or not axis.strip():
                errors.append(f"architecture_axes[{idx}] must be non-empty string.")

    hotspots = data.get("risk_hotspots")
    if not isinstance(hotspots, list):
        errors.append("'risk_hotspots' must be a list.")
    else:
        for idx, item in enumerate(hotspots):
            if not isinstance(item, dict):
                errors.append(f"risk_hotspots[{idx}] must be an object.")
                continue
            path = str(item.get("path", "")).strip()
            risk = str(item.get("risk", "")).strip()
            reason = str(item.get("reason", "")).strip()
            if path and not is_known_path(path, known_paths):
                errors.append(f"risk_hotspots[{idx}] path not in repository: {path}")
            if not risk:
                errors.append(f"risk_hotspots[{idx}] missing risk.")
            if not reason:
                errors.append(f"risk_hotspots[{idx}] missing reason.")

    return errors


def sanitize_navigation_brief(
    data: dict[str, Any],
    known_paths: set[str],
    *,
    reading_cap: int,
    axes_cap: int,
    hotspots_cap: int,
) -> dict[str, Any]:
    summary = str(data.get("summary", "")).strip()

    reading_order: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    for item in data.get("reading_order", []):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip()
        why = str(item.get("why", "")).strip()
        if not path or not why or not is_known_path(path, known_paths):
            continue
        normalized = path.rstrip("/")
        if normalized in seen_paths:
            continue
        seen_paths.add(normalized)
        reading_order.append({"path": path, "why": why})
        if len(reading_order) >= reading_cap:
            break

    architecture_axes: list[str] = []
    for axis in data.get("architecture_axes", []):
        if not isinstance(axis, str):
            continue
        axis_text = axis.strip()
        if not axis_text:
            continue
        architecture_axes.append(axis_text)
        if len(architecture_axes) >= axes_cap:
            break

    hotspots: list[dict[str, str]] = []
    for item in data.get("risk_hotspots", []):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip()
        risk = str(item.get("risk", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if not risk or not reason:
            continue
        if path and not is_known_path(path, known_paths):
            continue
        hotspots.append({"path": path, "risk": risk, "reason": reason})
        if len(hotspots) >= hotspots_cap:
            break

    return {
        "summary": summary,
        "reading_order": reading_order,
        "architecture_axes": architecture_axes,
        "risk_hotspots": hotspots,
    }


def build_navigation_brief_prompt(
    *,
    candidate_paths: set[str],
    context_payload: dict[str, Any],
    reading_cap: int,
    axes_cap: int,
    hotspots_cap: int,
) -> str:
    return (
        "You are preparing a navigation brief for another coding LLM.\n"
        "Use ONLY paths from this repository context. Never invent paths.\n"
        "Return JSON only with schema:\n"
        "{\n"
        '  "summary": "1-2 sentence repo orientation",\n'
        '  "reading_order": [{"path": "...", "why": "..."}],\n'
        '  "architecture_axes": ["..."],\n'
        '  "risk_hotspots": [{"path": "...", "risk": "...", "reason": "..."}]\n'
        "}\n"
        "Constraints:\n"
        f"- reading_order: {max(3, reading_cap - 1)}-{reading_cap} items\n"
        f"- architecture_axes: {max(2, axes_cap - 1)}-{axes_cap} items\n"
        f"- risk_hotspots: 0-{hotspots_cap} items\n"
        "- path fields must be from Allowed Paths.\n\n"
        f"Allowed Paths:\n{json.dumps(sorted(candidate_paths), ensure_ascii=True, indent=2)}\n\n"
        f"Repository Context:\n{json.dumps(context_payload, ensure_ascii=True, indent=2)}"
    )


def run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def render_llm_navigation_brief(
    brief: dict[str, Any],
    *,
    reading_cap: int,
    axes_cap: int,
    hotspots_cap: int,
) -> str:
    lines = ["## LLM Navigation Brief", ""]

    summary = str(brief.get("summary", "")).strip()
    if summary:
        lines.append(f"**Summary**: {summary}")
        lines.append("")

    reading = brief.get("reading_order", [])[:reading_cap]
    if reading:
        lines.append("### Suggested Reading Order")
        lines.append("")
        for idx, item in enumerate(reading, 1):
            lines.append(f"{idx}. `{item['path']}`: {item['why']}")
        lines.append("")

    axes = brief.get("architecture_axes", [])[:axes_cap]
    if axes:
        lines.append("### Architecture Axes")
        lines.append("")
        for axis in axes:
            lines.append(f"- {axis}")
        lines.append("")

    hotspots = brief.get("risk_hotspots", [])[:hotspots_cap]
    if hotspots:
        lines.append("### Risk Hotspots")
        lines.append("")
        for item in hotspots:
            path = item.get("path", "")
            risk = item.get("risk", "")
            reason = item.get("reason", "")
            if path:
                lines.append(f"- `{path}` ({risk}): {reason}")
            else:
                lines.append(f"- {risk}: {reason}")
        lines.append("")

    return "\n".join(lines)
