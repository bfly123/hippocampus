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


def _validate_required_summary(data: dict[str, Any], errors: list[str]) -> None:
    if not isinstance(data.get("summary"), str) or not data["summary"].strip():
        errors.append("Missing non-empty 'summary'.")


def _validate_reading_order(reading: Any, known_paths: set[str], errors: list[str]) -> None:
    if not isinstance(reading, list):
        errors.append("'reading_order' must be a list.")
        return
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


def _validate_axes(axes: Any, errors: list[str]) -> None:
    if not isinstance(axes, list):
        errors.append("'architecture_axes' must be a list.")
        return
    for idx, axis in enumerate(axes):
        if not isinstance(axis, str) or not axis.strip():
            errors.append(f"architecture_axes[{idx}] must be non-empty string.")


def _validate_hotspots(hotspots: Any, known_paths: set[str], errors: list[str]) -> None:
    if not isinstance(hotspots, list):
        errors.append("'risk_hotspots' must be a list.")
        return
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


def validate_navigation_brief_json(text: str, known_paths: set[str]) -> list[str]:
    errors: list[str] = []
    data = parse_json_block(text)
    if data is None:
        return ["Output must be a JSON object."]

    _validate_required_summary(data, errors)
    _validate_reading_order(data.get("reading_order"), known_paths, errors)
    _validate_axes(data.get("architecture_axes"), errors)
    _validate_hotspots(data.get("risk_hotspots"), known_paths, errors)

    return errors


def _sanitize_reading_order(
    items: list[Any],
    known_paths: set[str],
    cap: int,
) -> list[dict[str, str]]:
    reading_order: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    for item in items:
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
        if len(reading_order) >= cap:
            break
    return reading_order


def _sanitize_string_list(items: list[Any], cap: int) -> list[str]:
    values: list[str] = []
    for item in items:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text:
            continue
        values.append(text)
        if len(values) >= cap:
            break
    return values


def _sanitize_hotspots(
    items: list[Any],
    known_paths: set[str],
    cap: int,
) -> list[dict[str, str]]:
    hotspots: list[dict[str, str]] = []
    for item in items:
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
        if len(hotspots) >= cap:
            break
    return hotspots


def sanitize_navigation_brief(
    data: dict[str, Any],
    known_paths: set[str],
    *,
    reading_cap: int,
    axes_cap: int,
    hotspots_cap: int,
) -> dict[str, Any]:
    summary = str(data.get("summary", "")).strip()
    return {
        "summary": summary,
        "reading_order": _sanitize_reading_order(
            data.get("reading_order", []),
            known_paths,
            reading_cap,
        ),
        "architecture_axes": _sanitize_string_list(
            data.get("architecture_axes", []),
            axes_cap,
        ),
        "risk_hotspots": _sanitize_hotspots(
            data.get("risk_hotspots", []),
            known_paths,
            hotspots_cap,
        ),
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


def _append_heading(lines: list[str], title: str) -> None:
    lines.extend([title, ""])


def _append_reading_order(lines: list[str], reading: list[dict[str, str]]) -> None:
    if not reading:
        return
    _append_heading(lines, "### Suggested Reading Order")
    for idx, item in enumerate(reading, 1):
        lines.append(f"{idx}. `{item['path']}`: {item['why']}")
    lines.append("")


def _append_bullets(lines: list[str], title: str, values: list[str]) -> None:
    if not values:
        return
    _append_heading(lines, title)
    for value in values:
        lines.append(f"- {value}")
    lines.append("")


def _append_hotspots(lines: list[str], hotspots: list[dict[str, str]]) -> None:
    if not hotspots:
        return
    _append_heading(lines, "### Risk Hotspots")
    for item in hotspots:
        path = item.get("path", "")
        risk = item.get("risk", "")
        reason = item.get("reason", "")
        if path:
            lines.append(f"- `{path}` ({risk}): {reason}")
        else:
            lines.append(f"- {risk}: {reason}")
    lines.append("")


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

    _append_reading_order(lines, brief.get("reading_order", [])[:reading_cap])
    _append_bullets(lines, "### Architecture Axes", brief.get("architecture_axes", [])[:axes_cap])
    _append_hotspots(lines, brief.get("risk_hotspots", [])[:hotspots_cap])

    return "\n".join(lines)
