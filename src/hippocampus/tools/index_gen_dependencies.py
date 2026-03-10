"""Dependency analysis helpers for index generation."""

from __future__ import annotations

import ast
from collections import defaultdict
from typing import Any


def resolve_import_to_file(
    module_name: str,
    current_dir: str,
    files_index: dict[str, dict],
    target,
) -> list[str]:
    """Resolve a module import to actual file paths."""
    del current_dir, target
    results = []
    module_parts = module_name.split(".")
    potential_paths = [
        "/".join(module_parts) + ".py",
        "src/" + "/".join(module_parts) + ".py",
        "/".join(module_parts) + "/__init__.py",
        "src/" + "/".join(module_parts) + "/__init__.py",
    ]

    for potential_path in potential_paths:
        normalized = potential_path.replace("\\", "/")
        for file_path in files_index.keys():
            if not file_path.endswith(".py"):
                continue
            if file_path == normalized:
                results.append(file_path)
            elif file_path.endswith("/" + normalized):
                prefix = file_path[: -len(normalized) - 1]
                if not prefix or prefix.endswith("/"):
                    results.append(file_path)

    return results


def resolve_relative_import(
    module_name: str,
    level: int,
    current_dir: str,
    files_index: dict[str, dict],
    target,
) -> list[str]:
    """Resolve a relative import to actual file paths."""
    del target
    parts = current_dir.split("/")
    if level > len(parts):
        return []

    if level == 1:
        target_dir_parts = parts
    else:
        target_dir_parts = parts[: -(level - 1)]

    target_dir = "/".join(target_dir_parts)
    if module_name:
        module_parts = module_name.split(".")
        target_dir = target_dir + "/" + "/".join(module_parts)

    results = []
    potential_paths = [target_dir + ".py", target_dir + "/__init__.py"]
    for potential_path in potential_paths:
        normalized = potential_path.replace("\\", "/")
        for file_path in files_index.keys():
            if not file_path.endswith(".py"):
                continue
            if file_path == normalized or file_path.endswith("/" + normalized):
                results.append(file_path)
    return results


def compute_function_dependencies(
    files_index: dict[str, dict],
    target,
) -> dict[str, list[dict[str, Any]]]:
    """Compute function-to-function call relationships."""
    from ..constants import HIPPO_DIR, QUERIES_DIR
    from ..nav.extractor import extract_tags_from_file

    symbol_to_files: dict[str, list[str]] = defaultdict(list)
    file_functions: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    file_references: dict[str, list[tuple[str, int]]] = defaultdict(list)
    queries_dir = target / HIPPO_DIR / QUERIES_DIR

    for file_path in files_index.keys():
        full_path = target / file_path
        if not full_path.exists():
            continue

        if file_path.endswith(".py"):
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(content, filename=file_path)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        func_name = node.name
                        start_line = node.lineno
                        end_line = (
                            node.end_lineno
                            if hasattr(node, "end_lineno")
                            else start_line + 50
                        )
                        file_functions[file_path].append(
                            (func_name, start_line, end_line)
                        )
                        symbol_to_files[func_name].append(file_path)
            except (SyntaxError, UnicodeDecodeError):
                pass

        try:
            defs, refs = extract_tags_from_file(full_path, target, queries_dir)
            if not file_functions.get(file_path):
                for tag in defs:
                    if tag.kind == "def":
                        symbol_to_files[tag.name].append(file_path)
                        file_functions[file_path].append((tag.name, tag.line, tag.line + 100))

            for tag in refs:
                if tag.kind == "ref":
                    file_references[file_path].append((tag.name, tag.line))
        except Exception:
            continue

    function_deps: dict[str, list[tuple[str, int]]] = defaultdict(list)

    for source_file, refs in file_references.items():
        source_funcs_sorted = sorted(file_functions.get(source_file, []), key=lambda x: x[1])
        for ref_name, ref_line in refs:
            caller_func = None
            for func_name, func_start, func_end in source_funcs_sorted:
                if func_start <= ref_line <= func_end:
                    caller_func = func_name
                    break
                if func_start > ref_line:
                    break
            if not caller_func:
                continue

            target_files = symbol_to_files.get(ref_name, [])
            for target_file in target_files:
                target_funcs = [f[0] for f in file_functions.get(target_file, [])]
                if ref_name in target_funcs:
                    caller_key = f"{source_file}:{caller_func}"
                    callee_key = f"{target_file}:{ref_name}"
                    if caller_key != callee_key:
                        function_deps[caller_key].append((callee_key, ref_line))

    result: dict[str, list[dict[str, Any]]] = {}
    for caller_key, targets in function_deps.items():
        target_counts: dict[str, list[int]] = defaultdict(list)
        for callee_key, line in targets:
            target_counts[callee_key].append(line)
        result[caller_key] = [
            {
                "target": callee_key,
                "weight": len(lines),
                "lines": sorted(lines)[:5],
            }
            for callee_key, lines in target_counts.items()
        ]
    return result


def compute_module_dependencies(
    files_index: dict[str, dict],
    file_to_module: dict[str, str],
    target,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[str]]]:
    """Compute module-to-module and file-to-file dependencies from imports."""
    module_deps: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    file_deps: dict[str, set[str]] = defaultdict(set)

    for file_path, file_info in files_index.items():
        lang = file_info.get("lang", "")
        if lang != "python" and not file_path.endswith(".py"):
            continue

        source_module = file_to_module.get(file_path)
        if not source_module:
            continue

        full_path = target / file_path
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=file_path)
        except (SyntaxError, UnicodeDecodeError):
            continue

        imported_files = set()
        file_dir = str(full_path.parent.relative_to(target)).replace("\\", "/")

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    resolved = resolve_import_to_file(alias.name, file_dir, files_index, target)
                    if resolved:
                        imported_files.update(resolved)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if node.level > 0:
                        resolved = resolve_relative_import(
                            node.module, node.level, file_dir, files_index, target
                        )
                    else:
                        resolved = resolve_import_to_file(
                            node.module, file_dir, files_index, target
                        )
                    if resolved:
                        imported_files.update(resolved)

                for alias in node.names:
                    if alias.name == "*":
                        continue
                    if node.module:
                        full_module = f"{node.module}.{alias.name}"
                    else:
                        if node.level > 0:
                            resolved = resolve_relative_import(
                                alias.name, node.level, file_dir, files_index, target
                            )
                            if resolved:
                                imported_files.update(resolved)
                            continue
                        full_module = alias.name
                    resolved = resolve_import_to_file(full_module, file_dir, files_index, target)
                    if resolved:
                        imported_files.update(resolved)

        for imported_file in imported_files:
            target_module = file_to_module.get(imported_file)
            if target_module and target_module != source_module:
                module_deps[(source_module, target_module)].append((file_path, imported_file))
            if imported_file != file_path:
                file_deps[file_path].add(imported_file)

    result: dict[str, list[dict[str, Any]]] = {}
    module_targets: dict[str, list[tuple[str, int, list]]] = defaultdict(list)
    for (source_mod, target_mod), file_pairs in module_deps.items():
        module_targets[source_mod].append((target_mod, len(file_pairs), file_pairs))

    max_edges_per_module = 10
    for source_mod, targets in module_targets.items():
        top_targets = sorted(targets, key=lambda x: x[1], reverse=True)[:max_edges_per_module]
        result[source_mod] = [
            {
                "target": target_mod,
                "weight": weight,
                "files": file_pairs[:5],
            }
            for target_mod, weight, file_pairs in top_targets
        ]

    file_deps_result = {
        file_path: sorted(list(targets))
        for file_path, targets in file_deps.items()
    }
    return result, file_deps_result
