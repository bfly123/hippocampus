"""Import resolution helpers for dependency analysis."""

from __future__ import annotations

import ast


def _matching_python_files(files_index: dict[str, dict], normalized: str):
    for file_path in files_index.keys():
        if not file_path.endswith(".py"):
            continue
        if file_path == normalized:
            yield file_path
            continue
        if file_path.endswith("/" + normalized):
            prefix = file_path[: -len(normalized) - 1]
            if not prefix or prefix.endswith("/"):
                yield file_path


def resolve_import_to_file(
    module_name: str,
    current_dir: str,
    files_index: dict[str, dict],
    target,
) -> list[str]:
    """Resolve a module import to actual file paths."""
    del current_dir, target
    module_parts = module_name.split(".")
    potential_paths = [
        "/".join(module_parts) + ".py",
        "src/" + "/".join(module_parts) + ".py",
        "/".join(module_parts) + "/__init__.py",
        "src/" + "/".join(module_parts) + "/__init__.py",
    ]
    resolved = []
    for potential_path in potential_paths:
        resolved.extend(
            _matching_python_files(files_index, potential_path.replace("\\", "/"))
        )
    return resolved


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

    target_dir_parts = parts if level == 1 else parts[: -(level - 1)]
    target_dir = "/".join(target_dir_parts)
    if module_name:
        target_dir = target_dir + "/" + "/".join(module_name.split("."))

    resolved = []
    for candidate in (target_dir + ".py", target_dir + "/__init__.py"):
        normalized = candidate.replace("\\", "/")
        for file_path in files_index.keys():
            if file_path.endswith(".py") and (
                file_path == normalized or file_path.endswith("/" + normalized)
            ):
                resolved.append(file_path)
    return resolved


def _resolve_import_from_node(
    node: ast.ImportFrom,
    *,
    file_dir: str,
    files_index: dict[str, dict],
    target,
) -> list[str]:
    resolved_files: list[str] = []
    if node.module:
        if node.level > 0:
            resolved_files.extend(
                resolve_relative_import(node.module, node.level, file_dir, files_index, target)
            )
        else:
            resolved_files.extend(resolve_import_to_file(node.module, file_dir, files_index, target))

    for alias in node.names:
        if alias.name == "*":
            continue
        if node.module:
            resolved_files.extend(
                resolve_import_to_file(
                    f"{node.module}.{alias.name}",
                    file_dir,
                    files_index,
                    target,
                )
            )
        elif node.level > 0:
            resolved_files.extend(
                resolve_relative_import(alias.name, node.level, file_dir, files_index, target)
            )
        else:
            resolved_files.extend(resolve_import_to_file(alias.name, file_dir, files_index, target))
    return resolved_files


def resolve_import_candidates(
    node: ast.AST,
    *,
    file_dir: str,
    files_index: dict[str, dict],
    target,
) -> list[str]:
    if isinstance(node, ast.Import):
        return [
            resolved
            for alias in node.names
            for resolved in resolve_import_to_file(alias.name, file_dir, files_index, target)
        ]
    if isinstance(node, ast.ImportFrom):
        return _resolve_import_from_node(
            node,
            file_dir=file_dir,
            files_index=files_index,
            target=target,
        )
    return []


def iter_imported_files(
    tree: ast.AST,
    *,
    file_dir: str,
    files_index: dict[str, dict],
    target,
) -> set[str]:
    imported_files: set[str] = set()
    for node in ast.walk(tree):
        imported_files.update(
            resolve_import_candidates(
                node,
                file_dir=file_dir,
                files_index=files_index,
                target=target,
            )
        )
    return imported_files
