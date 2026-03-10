"""Treemap/statistics/snapshot trend transformers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def transform_files_to_treemap(tree: Dict[str, Any]) -> Dict[str, Any]:
    """Transform file tree to ECharts treemap format."""

    def convert_node(node: Dict) -> Dict:
        result = {"name": node.get("name", "unknown")}

        if node.get("type") == "file":
            result["value"] = node.get("size", 1)
        else:
            children = []
            for child in node.get("children", []):
                children.append(convert_node(child))
            result["children"] = children
            result["value"] = (
                sum(c.get("value", 0) for c in children) if children else 1
            )

        return result

    root = tree.get("root", tree)
    return convert_node(root)


def transform_modules_to_treemap(index: Dict[str, Any]) -> Dict[str, Any]:
    """Transform modules to treemap format (grouped by module)."""
    modules = index.get("modules", [])
    files_dict = index.get("files", {})
    files = list(files_dict.values()) if isinstance(files_dict, dict) else files_dict

    module_map = {}
    for file_info in files:
        module_name = file_info.get("module", "unknown")
        if module_name not in module_map:
            module_map[module_name] = []
        module_map[module_name].append(file_info)

    children = []
    for module in modules:
        module_id = module.get("id", "unknown")
        module_files = module_map.get(module_id, [])
        file_children = [
            {"name": f.get("name", f.get("id", "").split("/")[-1]), "value": 1}
            for f in module_files
        ]

        module_name = module_id.replace("mod:", "")
        children.append(
            {
                "name": module_name,
                "children": file_children,
                "value": sum(c["value"] for c in file_children)
                if file_children
                else 1,
            }
        )

    return {"name": "Project", "children": children}


def transform_stats_to_pie(index: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """Transform statistics to pie chart data."""
    modules = index.get("modules", [])
    files_dict = index.get("files", {})
    files = list(files_dict.values()) if isinstance(files_dict, dict) else files_dict

    role_counts = {}
    for module in modules:
        role = module.get("role") or module.get("tier", "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1

    role_data = [{"name": k, "value": v} for k, v in role_counts.items()]

    type_counts = {}
    for file_info in files:
        file_id = file_info.get("id", "")
        ext = file_id.split(".")[-1] if "." in file_id else "no_ext"
        type_counts[ext] = type_counts.get(ext, 0) + 1

    type_data = [{"name": k, "value": v} for k, v in type_counts.items()]

    return {
        "role_distribution": role_data,
        "tier_distribution": role_data,
        "file_type_distribution": type_data,
    }


def transform_snapshots_to_trends(snapshots_dir: Path) -> Dict[str, Any]:
    """Transform snapshot history to trend data."""
    if not snapshots_dir.exists():
        return {"dates": [], "file_counts": [], "module_counts": []}

    snapshots = []
    for snapshot_file in sorted(snapshots_dir.glob("*.json")):
        try:
            data = json.loads(snapshot_file.read_text())
            snapshots.append({"date": snapshot_file.stem, "data": data})
        except Exception:
            continue

    dates = [s["date"] for s in snapshots]
    file_counts = [len(s["data"].get("files", [])) for s in snapshots]
    module_counts = [len(s["data"].get("modules", [])) for s in snapshots]

    return {
        "dates": dates,
        "file_counts": file_counts,
        "module_counts": module_counts,
    }


__all__ = [
    "transform_files_to_treemap",
    "transform_modules_to_treemap",
    "transform_snapshots_to_trends",
    "transform_stats_to_pie",
]
