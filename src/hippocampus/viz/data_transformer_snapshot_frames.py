"""Snapshot frame transformers for module graph visualizations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def compute_frame_diff(prev_modules: List[Dict], curr_modules: List[Dict]) -> Dict[str, Any]:
    prev_ids = {m["id"] for m in prev_modules}
    curr_ids = {m["id"] for m in curr_modules}
    added = sorted(list(curr_ids - prev_ids))
    removed = sorted(list(prev_ids - curr_ids))
    prev_map = {m["id"]: m for m in prev_modules}

    changed = []
    for current_module in curr_modules:
        module_id = current_module["id"]
        if module_id not in prev_map:
            continue
        previous_module = prev_map[module_id]
        score_delta = current_module["core_score"] - previous_module["core_score"]
        tier_changed = current_module["tier"] != previous_module["tier"]
        role_changed = current_module.get("role", "") != previous_module.get("role", "")
        if abs(score_delta) <= 0.01 and not tier_changed and not role_changed:
            continue

        change_info = {"id": module_id, "score_delta": round(score_delta, 4)}
        if tier_changed:
            change_info["tier_change"] = f"{previous_module['tier']} -> {current_module['tier']}"
        if role_changed:
            change_info["role_change"] = (
                f"{previous_module.get('role', '?')} -> {current_module.get('role', '?')}"
            )
        changed.append(change_info)

    changed.sort(key=lambda item: item["id"])
    return {"added": added, "removed": removed, "changed": changed}


def _load_snapshots(snapshots_dir: Path) -> list[dict[str, Any]]:
    snapshots = []
    for snapshot_file in sorted(snapshots_dir.glob("*.json")):
        try:
            data = json.loads(snapshot_file.read_text())
        except Exception:
            continue
        meta = data.get("_snapshot", {})
        snapshots.append(
            {
                "snapshot_id": meta.get("snapshot_id", snapshot_file.stem),
                "timestamp": meta.get("snapshot_created_at", ""),
                "data": data,
            }
        )
    return snapshots


def _frame_date_label(timestamp: str, snapshot_id: str) -> str:
    try:
        from datetime import datetime

        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return snapshot_id[:15]


def _frame_links(snapshot: dict[str, Any], *, frame_module_ids: set[str]) -> list[dict[str, Any]]:
    links = []
    for source_mod, targets in snapshot["data"].get("module_dependencies", {}).items():
        if source_mod not in frame_module_ids:
            continue
        for target_info in targets:
            target_mod = target_info["target"]
            if target_mod not in frame_module_ids:
                continue
            weight = target_info["weight"]
            links.append(
                {
                    "source": source_mod,
                    "target": target_mod,
                    "lineStyle": {
                        "width": min(1 + weight / 5, 5),
                        "opacity": min(0.3 + weight / 30, 0.8),
                        "curveness": 0.2,
                    },
                }
            )
    return links


def _frame_modules(modules: list[dict[str, Any]], *, positions: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    frame_modules = []
    for module in modules:
        module_id = module.get("id", "unknown")
        pos = positions.get(module_id, {"x": 400, "y": 300})
        frame_modules.append(
            {
                "id": module_id,
                "name": module_id.replace("mod:", ""),
                "core_score": module.get("core_score", 0.5),
                "tier": module.get("tier", "unknown"),
                "role": module.get("role", ""),
                "file_count": module.get("file_count", 0),
                "x": pos["x"],
                "y": pos["y"],
            }
        )
    return frame_modules


def _animation_frames(snapshots: list[dict[str, Any]], *, positions: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    frames = []
    for snapshot in snapshots:
        modules = snapshot["data"].get("modules", [])
        frames.append(
            {
                "snapshot_id": snapshot["snapshot_id"],
                "timestamp": snapshot["timestamp"],
                "date_label": _frame_date_label(snapshot["timestamp"], snapshot["snapshot_id"]),
                "modules": _frame_modules(modules, positions=positions),
                "links": _frame_links(snapshot, frame_module_ids={m.get("id") for m in modules}),
            }
        )
    return frames


def transform_snapshots_to_frames(snapshots_dir: Path) -> Dict[str, Any]:
    if not snapshots_dir.exists():
        return {"frames": [], "diffs": [], "module_ids": []}

    snapshots = _load_snapshots(snapshots_dir)
    if not snapshots:
        return {"frames": [], "diffs": [], "module_ids": []}

    module_ids = sorted(
        {
            module.get("id", "unknown")
            for snapshot in snapshots
            for module in snapshot["data"].get("modules", [])
        }
    )
    from .data_transformer_module_graph import calculate_ring_positions

    positions = calculate_ring_positions(module_ids)
    frames = _animation_frames(snapshots, positions=positions)
    diffs = [
        {"from_index": idx - 1, "to_index": idx, **compute_frame_diff(frames[idx - 1]["modules"], frames[idx]["modules"])}
        for idx in range(1, len(frames))
    ]
    return {"frames": frames, "diffs": diffs, "module_ids": module_ids}
