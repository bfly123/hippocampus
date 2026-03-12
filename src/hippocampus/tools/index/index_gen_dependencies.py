"""Dependency analysis helpers for index generation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .index_gen_dependency_symbols import (
    collect_symbol_data,
    iter_function_dependency_edges,
    safe_parse_python_file,
)
from .index_gen_import_resolution import (
    iter_imported_files as _iter_imported_files,
    resolve_import_candidates as _resolve_import_candidates,
    resolve_import_to_file,
    resolve_relative_import,
)


def _summarize_function_dependencies(
    function_deps: dict[str, list[tuple[str, int]]],
) -> dict[str, list[dict[str, Any]]]:
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


def compute_function_dependencies(
    files_index: dict[str, dict],
    target,
) -> dict[str, list[dict[str, Any]]]:
    """Compute function-to-function call relationships."""
    symbol_to_files, file_functions, file_references = collect_symbol_data(files_index, target)

    function_deps: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for caller_key, callee_key, ref_line in iter_function_dependency_edges(
        file_references,
        file_functions,
        symbol_to_files,
    ):
        function_deps[caller_key].append((callee_key, ref_line))
    return _summarize_function_dependencies(function_deps)


def _record_dependency_edges(
    imported_files: set[str],
    *,
    file_path: str,
    source_module: str,
    file_to_module: dict[str, str],
    module_deps: dict[tuple[str, str], list[tuple[str, str]]],
    file_deps: dict[str, set[str]],
) -> None:
    for imported_file in imported_files:
        target_module = file_to_module.get(imported_file)
        if target_module and target_module != source_module:
            module_deps[(source_module, target_module)].append((file_path, imported_file))
        if imported_file != file_path:
            file_deps[file_path].add(imported_file)


def _summarize_module_dependencies(
    module_deps: dict[tuple[str, str], list[tuple[str, str]]],
    file_deps: dict[str, set[str]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[str]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    module_targets: dict[str, list[tuple[str, int, list[tuple[str, str]]]]] = defaultdict(list)
    for (source_mod, target_mod), file_pairs in module_deps.items():
        module_targets[source_mod].append((target_mod, len(file_pairs), file_pairs))

    max_edges_per_module = 10
    for source_mod, targets in module_targets.items():
        top_targets = sorted(targets, key=lambda item: item[1], reverse=True)[:max_edges_per_module]
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

        tree = safe_parse_python_file(full_path, filename=file_path)
        if tree is None:
            continue

        file_dir = str(full_path.parent.relative_to(target)).replace("\\", "/")
        imported_files = _iter_imported_files(
            tree,
            file_dir=file_dir,
            files_index=files_index,
            target=target,
        )
        _record_dependency_edges(
            imported_files,
            file_path=file_path,
            source_module=source_module,
            file_to_module=file_to_module,
            module_deps=module_deps,
            file_deps=file_deps,
        )

    return _summarize_module_dependencies(module_deps, file_deps)
