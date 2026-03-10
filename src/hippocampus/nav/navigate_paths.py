from __future__ import annotations

from pathlib import Path


def validate_repo_paths(files: list[str], index_files: set[str], root: Path) -> list[str]:
    """Filter file paths to keep only safe, indexed, repo-local paths."""
    root_resolved = root.resolve()
    index_lower = {item.lower() for item in index_files}
    validated: list[str] = []
    for file_path in files:
        normalized = _normalize_candidate(file_path=file_path)
        if not normalized:
            continue
        if normalized.lower() not in index_lower:
            continue
        if not _is_path_within_root(root=root_resolved, relative_path=normalized):
            continue
        validated.append(normalized)
    return validated


def _normalize_candidate(*, file_path: str) -> str:
    if not file_path or not isinstance(file_path, str):
        return ""
    normalized = file_path.replace("\\", "/").lstrip("/")
    if Path(normalized).is_absolute():
        return ""
    if ".." in normalized.split("/"):
        return ""
    try:
        return str(Path(normalized).as_posix())
    except (ValueError, RuntimeError):
        return ""


def _is_path_within_root(*, root: Path, relative_path: str) -> bool:
    try:
        full_path = (root / relative_path).resolve()
        return full_path.is_relative_to(root)
    except (ValueError, RuntimeError):
        return False
