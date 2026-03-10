"""Module graph and snapshot frame transformers."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List


ROLE_COLORS: dict[str, str] = {
    "core": "#6366F1",
    "infra": "#A855F7",
    "interface": "#14B8A6",
    "test": "#F59E0B",
    "docs": "#94A3B8",
}


def get_tier_color(tier: str) -> str:
    colors = {
        "core": "#1D4ED8",
        "secondary": "#0F766E",
        "peripheral": "#64748B",
        "unknown": "#D97706",
    }
    return colors.get(tier, "#D97706")


def get_role_color(role: str) -> str:
    return ROLE_COLORS.get(role, "#94A3B8")


def calculate_ring_positions(
    module_ids: List[str],
    center_x: float = 400,
    center_y: float = 300,
    radius: float = 200,
) -> Dict[str, Dict[str, float]]:
    positions = {}
    n = len(module_ids)
    if n == 0:
        return positions

    for i, module_id in enumerate(module_ids):
        angle = (2 * math.pi * i / n) - (math.pi / 2)
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        positions[module_id] = {"x": round(x, 2), "y": round(y, 2)}

    return positions


def calculate_role_positions(
    modules: List[Dict],
    center_x: float = 400,
    center_y: float = 300,
) -> Dict[str, Dict[str, float]]:
    role_groups: Dict[str, List[str]] = {}
    for module in modules:
        role = module.get("role", "core")
        role_groups.setdefault(role, []).append(module.get("id", "unknown"))

    inner_radius = 80
    outer_radius = 220

    sector_ranges = {
        "infra": (0, 120),
        "interface": (120, 240),
        "test": (240, 300),
        "docs": (300, 360),
    }

    positions = {}

    core_ids = role_groups.get("core", [])
    if core_ids:
        n = len(core_ids)
        for i, module_id in enumerate(core_ids):
            angle = (2 * math.pi * i / n) - (math.pi / 2)
            x = center_x + inner_radius * math.cos(angle)
            y = center_y + inner_radius * math.sin(angle)
            positions[module_id] = {"x": round(x, 2), "y": round(y, 2)}

    for role, (start_deg, end_deg) in sector_ranges.items():
        ids = role_groups.get(role, [])
        if not ids:
            continue

        start_rad = math.radians(start_deg) - (math.pi / 2)
        end_rad = math.radians(end_deg) - (math.pi / 2)
        n = len(ids)

        for i, module_id in enumerate(ids):
            if n == 1:
                angle = (start_rad + end_rad) / 2
            else:
                angle = start_rad + (end_rad - start_rad) * (i + 0.5) / n
            x = center_x + outer_radius * math.cos(angle)
            y = center_y + outer_radius * math.sin(angle)
            positions[module_id] = {"x": round(x, 2), "y": round(y, 2)}

    return positions


def calculate_tiered_positions(
    modules: List[Dict],
    center_x: float = 400,
    center_y: float = 300,
) -> Dict[str, Dict[str, float]]:
    tier_groups = {"core": [], "secondary": [], "peripheral": [], "unknown": []}

    for module in modules:
        tier = module.get("tier", "unknown")
        tier_groups[tier].append(module.get("id", "unknown"))

    tier_radii = {
        "core": 80,
        "secondary": 180,
        "peripheral": 280,
        "unknown": 280,
    }

    positions = {}

    for tier, module_ids in tier_groups.items():
        if not module_ids:
            continue

        radius = tier_radii[tier]
        n = len(module_ids)

        for i, module_id in enumerate(module_ids):
            angle = (2 * math.pi * i / n) - (math.pi / 2)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            positions[module_id] = {"x": round(x, 2), "y": round(y, 2)}

    return positions


def compute_frame_diff(prev_modules: List[Dict], curr_modules: List[Dict]) -> Dict[str, Any]:
    prev_ids = {m["id"] for m in prev_modules}
    curr_ids = {m["id"] for m in curr_modules}

    added = sorted(list(curr_ids - prev_ids))
    removed = sorted(list(prev_ids - curr_ids))

    prev_map = {m["id"]: m for m in prev_modules}

    changed = []
    for curr_m in curr_modules:
        module_id = curr_m["id"]
        if module_id in prev_map:
            prev_m = prev_map[module_id]
            score_delta = curr_m["core_score"] - prev_m["core_score"]
            tier_changed = curr_m["tier"] != prev_m["tier"]
            role_changed = curr_m.get("role", "") != prev_m.get("role", "")

            if abs(score_delta) > 0.01 or tier_changed or role_changed:
                change_info = {"id": module_id, "score_delta": round(score_delta, 4)}
                if tier_changed:
                    change_info["tier_change"] = f"{prev_m['tier']} -> {curr_m['tier']}"
                if role_changed:
                    change_info["role_change"] = (
                        f"{prev_m.get('role', '?')} -> {curr_m.get('role', '?')}"
                    )
                changed.append(change_info)

    changed.sort(key=lambda x: x["id"])

    return {"added": added, "removed": removed, "changed": changed}


def transform_modules_to_graph(index: Dict[str, Any]) -> Dict[str, Any]:
    modules = index.get("modules", [])
    files_dict = index.get("files", {})
    file_dependencies = index.get("file_dependencies", {})

    module_files_map = {}
    for file_path, file_info in files_dict.items():
        module_id = file_info.get("module", "unknown")
        if module_id not in module_files_map:
            module_files_map[module_id] = []
        module_files_map[module_id].append(
            {
                "path": file_path,
                "name": file_info.get("name", file_path.split("/")[-1]),
                "desc": file_info.get("desc", ""),
                "signatures": file_info.get("signatures", []),
                "dependencies": file_dependencies.get(file_path, []),
            }
        )

    nodes = []
    for module in modules:
        module_id = module.get("id", "unknown")
        module_name = module_id.replace("mod:", "")

        base_size = 28
        max_extra = 36
        core_score = module.get("core_score", 0.5)
        size = base_size + (math.sqrt(core_score) * max_extra)

        role = module.get("role", "core")
        node = {
            "id": module_id,
            "name": module_name,
            "symbolSize": size,
            "value": core_score,
            "category": role,
            "role": role,
            "label": {
                "show": True,
                "position": "inside" if size >= 60 else "right",
                "fontSize": 14 if size >= 60 else 12,
                "color": "#fff" if size >= 60 else "#333",
            },
            "itemStyle": {"color": get_role_color(role)},
            "desc": module.get("desc", ""),
            "file_count": module.get("file_count", 0),
            "key_files": module.get("key_files", []),
            "core_score": core_score,
            "files": module_files_map.get(module_id, []),
        }
        nodes.append(node)

    links = []
    module_deps = index.get("module_dependencies", {})

    for source_mod, targets in module_deps.items():
        for target_info in targets:
            target_mod = target_info["target"]
            weight = target_info["weight"]

            links.append(
                {
                    "source": source_mod,
                    "target": target_mod,
                    "value": weight,
                    "lineStyle": {
                        "width": min(1 + weight / 5, 5),
                        "opacity": min(0.3 + weight / 30, 0.8),
                        "curveness": 0.2,
                    },
                }
            )

    positions = calculate_role_positions(modules)

    return {
        "nodes": nodes,
        "links": links,
        "positions": positions,
        "categories": [
            {"name": role, "itemStyle": {"color": ROLE_COLORS[role]}}
            for role in ("core", "infra", "interface", "test", "docs")
        ],
    }


def transform_snapshots_to_frames(snapshots_dir: Path) -> Dict[str, Any]:
    if not snapshots_dir.exists():
        return {"frames": [], "diffs": [], "module_ids": []}

    snapshots = []
    for snapshot_file in sorted(snapshots_dir.glob("*.json")):
        try:
            data = json.loads(snapshot_file.read_text())
            meta = data.get("_snapshot", {})
            snapshots.append(
                {
                    "snapshot_id": meta.get("snapshot_id", snapshot_file.stem),
                    "timestamp": meta.get("snapshot_created_at", ""),
                    "data": data,
                }
            )
        except Exception:
            continue

    if not snapshots:
        return {"frames": [], "diffs": [], "module_ids": []}

    all_module_ids = set()
    for snapshot in snapshots:
        modules = snapshot["data"].get("modules", [])
        for module in modules:
            all_module_ids.add(module.get("id", "unknown"))

    module_ids = sorted(all_module_ids)
    positions = calculate_ring_positions(module_ids)

    frames = []
    for snapshot in snapshots:
        modules = snapshot["data"].get("modules", [])

        timestamp = snapshot["timestamp"]
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            date_label = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            date_label = snapshot["snapshot_id"][:15]

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

        frame_links = []
        module_deps = snapshot["data"].get("module_dependencies", {})
        frame_module_ids = {m.get("id") for m in modules}

        for source_mod, targets in module_deps.items():
            if source_mod not in frame_module_ids:
                continue
            for target_info in targets:
                target_mod = target_info["target"]
                if target_mod not in frame_module_ids:
                    continue
                weight = target_info["weight"]
                frame_links.append(
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

        frames.append(
            {
                "snapshot_id": snapshot["snapshot_id"],
                "timestamp": timestamp,
                "date_label": date_label,
                "modules": frame_modules,
                "links": frame_links,
            }
        )

    diffs = []
    for i in range(1, len(frames)):
        diff = compute_frame_diff(frames[i - 1]["modules"], frames[i]["modules"])
        diffs.append({"from_index": i - 1, "to_index": i, **diff})

    return {
        "frames": frames,
        "diffs": diffs,
        "module_ids": module_ids,
    }


__all__ = [
    "ROLE_COLORS",
    "calculate_ring_positions",
    "calculate_role_positions",
    "calculate_tiered_positions",
    "compute_frame_diff",
    "get_role_color",
    "get_tier_color",
    "transform_modules_to_graph",
    "transform_snapshots_to_frames",
]
