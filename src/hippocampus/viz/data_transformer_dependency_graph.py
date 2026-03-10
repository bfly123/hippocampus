"""File/function dependency graph transformers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .data_transformer_module_graph import get_role_color, get_tier_color


def transform_files_to_graph(index: Dict[str, Any]) -> Dict[str, Any]:
    """Transform file dependencies to ECharts graph format."""
    files_dict = index.get("files", {})
    file_dependencies = index.get("file_dependencies", {})
    modules = index.get("modules", [])

    module_colors = {}
    for module in modules:
        module_id = module.get("id", "unknown")
        role = module.get("role")
        if role:
            module_colors[module_id] = get_role_color(role)
        else:
            module_colors[module_id] = get_tier_color(module.get("tier", "unknown"))

    nodes = []
    for file_path, file_info in files_dict.items():
        module_id = file_info.get("module", "unknown")
        sig_count = len(file_info.get("signatures", []))

        base_size = 15
        size = base_size + min(sig_count * 2, 30)

        node = {
            "id": file_path,
            "name": file_info.get("name", file_path.split("/")[-1]),
            "symbolSize": size,
            "value": sig_count,
            "category": module_id,
            "label": {"show": True, "fontSize": 10},
            "itemStyle": {"color": module_colors.get(module_id, "#64748B")},
            "module": module_id,
            "path": file_path,
            "desc": file_info.get("desc", ""),
            "lang": file_info.get("lang", "unknown"),
            "signatures": file_info.get("signatures", []),
            "dependencies": file_dependencies.get(file_path, []),
        }
        nodes.append(node)

    links = []
    for source_file, target_files in file_dependencies.items():
        for target_file in target_files:
            if source_file in files_dict and target_file in files_dict:
                source_module = files_dict[source_file].get("module")
                target_module = files_dict[target_file].get("module")
                is_cross_module = source_module != target_module

                links.append(
                    {
                        "source": source_file,
                        "target": target_file,
                        "lineStyle": {
                            "width": 2 if is_cross_module else 1,
                            "opacity": 0.6 if is_cross_module else 0.3,
                            "curveness": 0.2,
                            "color": "#E11D48" if is_cross_module else "#94A3B8",
                        },
                        "cross_module": is_cross_module,
                    }
                )

    categories = [{"name": module.get("id", "unknown")} for module in modules]

    return {"nodes": nodes, "links": links, "categories": categories}


def transform_functions_to_graph(
    index: Dict[str, Any],
    focus_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Transform function dependencies to ECharts graph format."""
    function_dependencies = index.get("function_dependencies", {})
    files_dict = index.get("files", {})

    if focus_file:
        relevant_funcs = set()
        for func_key in function_dependencies.keys():
            file_path = func_key.split(":")[0]
            if file_path == focus_file:
                relevant_funcs.add(func_key)
                for dep in function_dependencies[func_key]:
                    relevant_funcs.add(dep["target"])

        for func_key, deps in function_dependencies.items():
            for dep in deps:
                target_file = dep["target"].split(":")[0]
                if target_file == focus_file:
                    relevant_funcs.add(func_key)
                    relevant_funcs.add(dep["target"])
    else:
        relevant_funcs = set(function_dependencies.keys())
        for deps in function_dependencies.values():
            for dep in deps:
                relevant_funcs.add(dep["target"])

    if len(relevant_funcs) > 200:
        relevant_funcs = set(list(relevant_funcs)[:200])

    nodes = []
    for func_key in relevant_funcs:
        parts = func_key.split(":", 1)
        if len(parts) != 2:
            continue
        file_path, func_name = parts

        file_info = files_dict.get(file_path, {})
        module_id = file_info.get("module", "unknown")

        is_focus = focus_file and file_path == focus_file

        node = {
            "id": func_key,
            "name": func_name,
            "symbolSize": 25 if is_focus else 15,
            "category": module_id,
            "label": {"show": True, "fontSize": 11 if is_focus else 9},
            "itemStyle": {
                "borderWidth": 2 if is_focus else 0,
                "borderColor": "#E11D48" if is_focus else None,
            },
            "file": file_path,
            "module": module_id,
        }
        nodes.append(node)

    links = []
    for source_key, deps in function_dependencies.items():
        if source_key not in relevant_funcs:
            continue

        for dep in deps:
            target_key = dep["target"]
            if target_key not in relevant_funcs:
                continue

            weight = dep.get("weight", 1)

            links.append(
                {
                    "source": source_key,
                    "target": target_key,
                    "value": weight,
                    "lineStyle": {
                        "width": min(1 + weight / 2, 4),
                        "opacity": min(0.4 + weight / 10, 0.8),
                        "curveness": 0.2,
                    },
                }
            )

    return {"nodes": nodes, "links": links, "categories": []}


__all__ = ["transform_files_to_graph", "transform_functions_to_graph"]
