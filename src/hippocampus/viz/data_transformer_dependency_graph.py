"""File/function dependency graph transformers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .data_transformer_module_graph import get_role_color, get_tier_color


def _module_color_map(modules: list[dict[str, Any]]) -> dict[str, str]:
    colors: dict[str, str] = {}
    for module in modules:
        module_id = module.get("id", "unknown")
        role = module.get("role")
        colors[module_id] = (
            get_role_color(role) if role else get_tier_color(module.get("tier", "unknown"))
        )
    return colors


def _file_graph_node(
    file_path: str,
    file_info: dict[str, Any],
    *,
    module_colors: dict[str, str],
    file_dependencies: dict[str, list[str]],
) -> dict[str, Any]:
    module_id = file_info.get("module", "unknown")
    sig_count = len(file_info.get("signatures", []))
    size = 15 + min(sig_count * 2, 30)
    return {
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


def _file_graph_link(
    source_file: str,
    target_file: str,
    *,
    files_dict: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_module = files_dict[source_file].get("module")
    target_module = files_dict[target_file].get("module")
    is_cross_module = source_module != target_module
    return {
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


def _collect_relevant_functions(
    function_dependencies: dict[str, list[dict[str, Any]]],
    *,
    focus_file: Optional[str],
) -> set[str]:
    if not focus_file:
        relevant_funcs = set(function_dependencies.keys())
        for deps in function_dependencies.values():
            for dep in deps:
                relevant_funcs.add(dep["target"])
        return relevant_funcs

    relevant_funcs: set[str] = set()
    for func_key, deps in function_dependencies.items():
        file_path = func_key.split(":")[0]
        if file_path == focus_file:
            relevant_funcs.add(func_key)
            relevant_funcs.update(dep["target"] for dep in deps)
            continue
        for dep in deps:
            if dep["target"].split(":")[0] == focus_file:
                relevant_funcs.add(func_key)
                relevant_funcs.add(dep["target"])
    return relevant_funcs


def _function_graph_node(
    func_key: str,
    *,
    files_dict: dict[str, dict[str, Any]],
    focus_file: Optional[str],
) -> dict[str, Any] | None:
    parts = func_key.split(":", 1)
    if len(parts) != 2:
        return None
    file_path, func_name = parts
    file_info = files_dict.get(file_path, {})
    module_id = file_info.get("module", "unknown")
    is_focus = bool(focus_file and file_path == focus_file)
    return {
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


def _function_graph_link(source_key: str, dep: dict[str, Any]) -> dict[str, Any]:
    weight = dep.get("weight", 1)
    return {
        "source": source_key,
        "target": dep["target"],
        "value": weight,
        "lineStyle": {
            "width": min(1 + weight / 2, 4),
            "opacity": min(0.4 + weight / 10, 0.8),
            "curveness": 0.2,
        },
    }


def transform_files_to_graph(index: Dict[str, Any]) -> Dict[str, Any]:
    """Transform file dependencies to ECharts graph format."""
    files_dict = index.get("files", {})
    file_dependencies = index.get("file_dependencies", {})
    modules = index.get("modules", [])
    module_colors = _module_color_map(modules)
    nodes = [
        _file_graph_node(
            file_path,
            file_info,
            module_colors=module_colors,
            file_dependencies=file_dependencies,
        )
        for file_path, file_info in files_dict.items()
    ]

    links = []
    for source_file, target_files in file_dependencies.items():
        for target_file in target_files:
            if source_file in files_dict and target_file in files_dict:
                links.append(_file_graph_link(source_file, target_file, files_dict=files_dict))

    categories = [{"name": module.get("id", "unknown")} for module in modules]

    return {"nodes": nodes, "links": links, "categories": categories}


def transform_functions_to_graph(
    index: Dict[str, Any],
    focus_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Transform function dependencies to ECharts graph format."""
    function_dependencies = index.get("function_dependencies", {})
    files_dict = index.get("files", {})
    relevant_funcs = _collect_relevant_functions(
        function_dependencies,
        focus_file=focus_file,
    )

    if len(relevant_funcs) > 200:
        relevant_funcs = set(list(relevant_funcs)[:200])

    nodes = []
    for func_key in relevant_funcs:
        node = _function_graph_node(func_key, files_dict=files_dict, focus_file=focus_file)
        if node is not None:
            nodes.append(node)

    links = []
    for source_key, deps in function_dependencies.items():
        if source_key not in relevant_funcs:
            continue

        for dep in deps:
            target_key = dep["target"]
            if target_key not in relevant_funcs:
                continue
            links.append(_function_graph_link(source_key, dep))

    return {"nodes": nodes, "links": links, "categories": []}


__all__ = ["transform_files_to_graph", "transform_functions_to_graph"]
