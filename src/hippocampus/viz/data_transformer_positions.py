"""Position calculators for graph visualizations."""

from __future__ import annotations

import math
from typing import Dict, List


def _polar_position(angle: float, *, center_x: float, center_y: float, radius: float) -> dict[str, float]:
    x = center_x + radius * math.cos(angle)
    y = center_y + radius * math.sin(angle)
    return {"x": round(x, 2), "y": round(y, 2)}


def _group_module_ids_by(modules: List[dict], key: str, *, default: str) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = {}
    for module in modules:
        groups.setdefault(module.get(key, default), []).append(module.get("id", "unknown"))
    return groups


def calculate_ring_positions(
    module_ids: List[str],
    center_x: float = 400,
    center_y: float = 300,
    radius: float = 200,
) -> Dict[str, Dict[str, float]]:
    positions = {}
    total = len(module_ids)
    if total == 0:
        return positions

    for index, module_id in enumerate(module_ids):
        angle = (2 * math.pi * index / total) - (math.pi / 2)
        positions[module_id] = _polar_position(
            angle,
            center_x=center_x,
            center_y=center_y,
            radius=radius,
        )
    return positions


def calculate_role_positions(
    modules: List[dict],
    center_x: float = 400,
    center_y: float = 300,
) -> Dict[str, Dict[str, float]]:
    role_groups = _group_module_ids_by(modules, "role", default="core")
    positions = {}

    core_ids = role_groups.get("core", [])
    for index, module_id in enumerate(core_ids):
        angle = (2 * math.pi * index / len(core_ids)) - (math.pi / 2)
        positions[module_id] = _polar_position(
            angle,
            center_x=center_x,
            center_y=center_y,
            radius=80,
        )

    for role, (start_deg, end_deg) in {
        "infra": (0, 120),
        "interface": (120, 240),
        "test": (240, 300),
        "docs": (300, 360),
    }.items():
        role_ids = role_groups.get(role, [])
        if not role_ids:
            continue
        start_rad = math.radians(start_deg) - (math.pi / 2)
        end_rad = math.radians(end_deg) - (math.pi / 2)
        count = len(role_ids)
        for index, module_id in enumerate(role_ids):
            angle = (
                (start_rad + end_rad) / 2
                if count == 1
                else start_rad + (end_rad - start_rad) * (index + 0.5) / count
            )
            positions[module_id] = _polar_position(
                angle,
                center_x=center_x,
                center_y=center_y,
                radius=220,
            )

    return positions


def calculate_tiered_positions(
    modules: List[dict],
    center_x: float = 400,
    center_y: float = 300,
) -> Dict[str, Dict[str, float]]:
    tier_groups = {
        "core": [],
        "secondary": [],
        "peripheral": [],
        "unknown": [],
    }
    for tier, module_ids in _group_module_ids_by(modules, "tier", default="unknown").items():
        tier_groups.setdefault(tier, []).extend(module_ids)

    positions = {}
    for tier, module_ids in tier_groups.items():
        if not module_ids:
            continue
        radius = {"core": 80, "secondary": 180, "peripheral": 280, "unknown": 280}[tier]
        for index, module_id in enumerate(module_ids):
            angle = (2 * math.pi * index / len(module_ids)) - (math.pi / 2)
            positions[module_id] = _polar_position(
                angle,
                center_x=center_x,
                center_y=center_y,
                radius=radius,
            )
    return positions
