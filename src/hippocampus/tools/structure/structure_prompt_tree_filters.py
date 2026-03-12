"""Filtering helpers for structure prompt tree rendering."""

from __future__ import annotations

from typing import Iterable

_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        "build",
        "dist",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        ".venv",
        "venv",
        "env",
        ".aider.tags.cache.v4",
        ".llmproxy",
        ".ccb",
        ".hippocampus",
        "vendor",
        "tmp",
        "tmp_hippo_llm_smoke",
        "fangan",
        "plans",
        "claude_skills",
    }
)
_SKIP_DIR_SUFFIXES = frozenset({".egg-info"})
_SKIP_PATH_PARTS = frozenset({"history", "snapshots"})
_KEEP_HIDDEN_DIRS = frozenset({".github", ".devcontainer"})
_SKIP_FILE_SUFFIXES = frozenset({".log", ".pid", ".tmp", ".cache", ".val", ".pyc", ".pyo"})
_SKIP_FILE_NAMES = frozenset({".ds_store", "thumbs.db"})


def normalized_parts(parts: Iterable[str]) -> tuple[str, ...]:
    return tuple(part for part in parts if part and part != ".")


def split_path(path: str) -> tuple[str, ...]:
    return normalized_parts(str(path or "").replace("\\", "/").split("/"))


def is_noise_path_parts(parts: tuple[str, ...]) -> bool:
    return any(part.lower() in _SKIP_PATH_PARTS for part in parts)


def is_noise_file_path(file_path: str) -> bool:
    parts = split_path(file_path)
    if not parts:
        return False
    lower_parts = [part.lower() for part in parts]
    name = lower_parts[-1]
    return (
        any(part in _SKIP_DIR_NAMES for part in lower_parts)
        or any(part in _SKIP_PATH_PARTS for part in lower_parts)
        or name in _SKIP_FILE_NAMES
        or any(name.endswith(suffix) for suffix in _SKIP_FILE_SUFFIXES)
    )


def skip_dir(name: str, parent_parts: tuple[str, ...] = ()) -> bool:
    if name == ".":
        return False
    lower = name.lower()
    if lower in _SKIP_DIR_NAMES:
        return True
    if any(lower.endswith(suffix) for suffix in _SKIP_DIR_SUFFIXES):
        return True
    if lower.startswith(".") and lower not in _KEEP_HIDDEN_DIRS:
        return True
    return is_noise_path_parts(normalized_parts(parent_parts + (name,)))


def skip_file(name: str, parent_parts: tuple[str, ...]) -> bool:
    lower = name.lower()
    if lower in _SKIP_FILE_NAMES:
        return True
    if any(lower.endswith(suffix) for suffix in _SKIP_FILE_SUFFIXES):
        return True
    if lower.startswith(".") and lower not in {".gitignore", ".env.example"}:
        return True
    return is_noise_path_parts(normalized_parts(parent_parts + (name,)))
