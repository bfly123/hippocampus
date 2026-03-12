"""Module graph transformers."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List

from .data_transformer_positions import (
    calculate_ring_positions,
    calculate_role_positions,
    calculate_tiered_positions,
)
from .data_transformer_snapshot_frames import (
    compute_frame_diff as compute_frame_diff_impl,
    transform_snapshots_to_frames as transform_snapshots_to_frames_impl,
)


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


def _build_module_files_map(
    files_dict: Dict[str, Dict[str, Any]],
    file_dependencies: Dict[str, List[str]],
) -> Dict[str, List[Dict[str, Any]]]:
    module_files_map: Dict[str, List[Dict[str, Any]]] = {}
    for file_path, file_info in files_dict.items():
        module_id = file_info.get("module", "unknown")
        module_files_map.setdefault(module_id, []).append(
            {
                "path": file_path,
                "name": file_info.get("name", file_path.split("/")[-1]),
                "desc": file_info.get("desc", ""),
                "signatures": file_info.get("signatures", []),
                "dependencies": file_dependencies.get(file_path, []),
            }
        )
    return module_files_map


def _build_graph_node(module: Dict[str, Any], module_files_map: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    module_id = module.get("id", "unknown")
    module_name = module_id.replace("mod:", "")
    base_size = 28
    max_extra = 36
    core_score = module.get("core_score", 0.5)
    size = base_size + (math.sqrt(core_score) * max_extra)
    role = module.get("role", "core")
    return {
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


def _build_graph_links(module_deps: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    links: List[Dict[str, Any]] = []
    for source_mod, targets in module_deps.items():
        for target_info in targets:
            weight = target_info["weight"]
            links.append(
                {
                    "source": source_mod,
                    "target": target_info["target"],
                    "value": weight,
                    "lineStyle": {
                        "width": min(1 + weight / 5, 5),
                        "opacity": min(0.3 + weight / 30, 0.8),
                        "curveness": 0.2,
                    },
                }
            )
    return links


def compute_frame_diff(prev_modules: List[Dict], curr_modules: List[Dict]) -> Dict[str, Any]:
    return compute_frame_diff_impl(prev_modules, curr_modules)


def transform_modules_to_graph(index: Dict[str, Any]) -> Dict[str, Any]:
    modules = index.get("modules", [])
    files_dict = index.get("files", {})
    file_dependencies = index.get("file_dependencies", {})
    module_files_map = _build_module_files_map(files_dict, file_dependencies)
    nodes = [_build_graph_node(module, module_files_map) for module in modules]
    links = _build_graph_links(index.get("module_dependencies", {}))
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
    return transform_snapshots_to_frames_impl(snapshots_dir)


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
