"""Generic strategy helpers for structure prompt generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .structure_strategy_support import (
    ARCHETYPE_FALLBACK_DESCRIPTIONS,
    ARCHETYPE_FRONTEND,
    ARCHETYPE_GENERIC,
    ARCHETYPE_INFRA,
    ARCHETYPE_LIBRARY,
    ARCHETYPE_MONOREPO,
    ARCHETYPE_SERVICE,
    ARCHETYPE_VALUES,
    BASE_ENTRY_FILE_REASONS,
    FRONTEND_ENTRY_FILE_REASONS,
    GENERIC_DIR_DESCRIPTIONS,
    INFRA_ENTRY_FILE_REASONS,
    PATH_ARCHETYPE_RULES,
    SERVICE_ENTRY_FILE_REASONS,
    TOKEN_DIR_DESCRIPTIONS,
    is_frontend_path,
    is_infra_path,
    is_library_path,
    is_service_path,
)

_PATH_PREDICATES: dict[str, Callable[[str], bool]] = {
    "_is_frontend_path": is_frontend_path,
    "_is_infra_path": is_infra_path,
    "_is_service_path": is_service_path,
    "_is_library_path": is_library_path,
}


def normalize_archetype(value: str | None) -> str:
    if not value:
        return ARCHETYPE_GENERIC
    normalized = value.strip().lower()
    return normalized if normalized in ARCHETYPE_VALUES else ARCHETYPE_GENERIC


def _build_top_level_stats(paths: list[str]) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    marker_names = {
        "pyproject.toml",
        "package.json",
        "go.mod",
        "cargo.toml",
        "pom.xml",
        "build.gradle",
    }
    for file_path in paths:
        parts = Path(file_path).as_posix().split("/")
        if not parts:
            continue
        stat = stats.setdefault(parts[0], {"files": 0, "markers": 0})
        stat["files"] += 1
        if parts[-1].lower() in marker_names:
            stat["markers"] += 1
        if "src" in {part.lower() for part in parts[1:]}:
            stat["markers"] += 1
    return stats


def _module_desc_archetype(modules: list[dict[str, Any]]) -> str | None:
    module_desc = " ".join(str(module.get("desc", "")).lower() for module in modules[:16])
    if any(token in module_desc for token in ("gateway", "proxy", "router", "server")):
        return ARCHETYPE_SERVICE
    if any(token in module_desc for token in ("indexing", "parser", "library", "sdk")):
        return ARCHETYPE_LIBRARY
    return None


def _multi_project_count(top_level_stats: dict[str, dict[str, int]]) -> int:
    return sum(
        1
        for stats in top_level_stats.values()
        if stats["files"] >= 8 and stats["markers"] >= 1
    )


def _count_path_hits(paths: list[str], predicate: Callable[[str], bool]) -> int:
    return sum(1 for path in paths if predicate(path))


def _detect_path_archetype(paths: list[str]) -> str | None:
    for archetype, threshold, predicate_name in PATH_ARCHETYPE_RULES:
        predicate = _PATH_PREDICATES[predicate_name]
        if _count_path_hits(paths, predicate) >= threshold:
            return archetype
    return None


def _root_name_archetype(root_name: str) -> str | None:
    return ARCHETYPE_INFRA if root_name.lower() in {"infra", "infrastructure", "ops"} else None


def detect_repo_archetype(
    root_name: str,
    files: dict[str, dict[str, Any]],
    modules: list[dict[str, Any]],
) -> str:
    """Infer repository archetype from paths and module metadata."""
    paths = list(files)
    if not paths:
        return ARCHETYPE_GENERIC

    if _multi_project_count(_build_top_level_stats(paths)) >= 2:
        return ARCHETYPE_MONOREPO

    lower_paths = [path.lower() for path in paths]
    return (
        _detect_path_archetype(lower_paths)
        or _module_desc_archetype(modules)
        or _root_name_archetype(root_name)
        or ARCHETYPE_GENERIC
    )


def _match_dir_description(name: str) -> str | None:
    for tokens, description in TOKEN_DIR_DESCRIPTIONS:
        if any(token in name for token in tokens):
            return description
    return None


def describe_workspace_dir(name: str, archetype: str) -> str:
    """Provide a generic semantic hint for top-level directories."""
    normalized = name.lower()
    archetype = normalize_archetype(archetype)
    return (
        GENERIC_DIR_DESCRIPTIONS.get(normalized)
        or _match_dir_description(normalized)
        or ARCHETYPE_FALLBACK_DESCRIPTIONS.get(archetype, "Workspace module")
    )


def entry_file_reasons_for_archetype(archetype: str) -> dict[str, str]:
    archetype = normalize_archetype(archetype)
    reasons = dict(BASE_ENTRY_FILE_REASONS)
    if archetype in {ARCHETYPE_SERVICE, ARCHETYPE_MONOREPO}:
        reasons.update(SERVICE_ENTRY_FILE_REASONS)
    if archetype in {ARCHETYPE_FRONTEND, ARCHETYPE_MONOREPO}:
        reasons.update(FRONTEND_ENTRY_FILE_REASONS)
    if archetype == ARCHETYPE_INFRA:
        reasons.update(INFRA_ENTRY_FILE_REASONS)
    return reasons
