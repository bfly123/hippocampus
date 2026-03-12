"""Import parsing helpers for graph ranker."""

from __future__ import annotations


def relative_import_paths(module_path: str, current_dir: str) -> list[str]:
    dots = len(module_path) - len(module_path.lstrip("."))
    suffix = module_path.lstrip(".").replace(".", "/")
    dir_parts = current_dir.split("/") if current_dir else []
    if dots > 1:
        dir_parts = dir_parts[: -(dots - 1)]
    base_dir = "/".join(part for part in dir_parts if part)
    if not suffix:
        return []
    prefix = f"{base_dir}/{suffix}" if base_dir else suffix
    return [f"{prefix}.py", f"{prefix}/__init__.py"]


def absolute_import_paths(module_path: str) -> list[str]:
    file_path = module_path.replace(".", "/")
    return [
        f"src/{file_path}.py",
        f"{file_path}.py",
        f"src/{file_path}/__init__.py",
    ]


def _extract_module_path(line: str) -> tuple[str, bool] | None:
    parts = line.split()
    if len(parts) < 2:
        return None
    return (parts[1], line.startswith("from "))


def extract_imports(content: str, file_path: str) -> list[str]:
    imports = []
    path_parts = file_path.split("/")
    current_dir = "/".join(path_parts[:-1]) if len(path_parts) > 1 else ""

    for raw_line in content.split("\n"):
        line = raw_line.strip()
        if not (line.startswith("import ") or line.startswith("from ")):
            continue
        module_info = _extract_module_path(line)
        if module_info is None:
            continue
        module_path, is_from_import = module_info
        if is_from_import and module_path.startswith("."):
            imports.extend(relative_import_paths(module_path, current_dir))
        else:
            absolute_paths = absolute_import_paths(module_path.split(",")[0].strip())
            imports.extend(absolute_paths if is_from_import else absolute_paths[:2])
    return imports
