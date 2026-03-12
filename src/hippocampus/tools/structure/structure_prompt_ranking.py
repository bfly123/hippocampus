from __future__ import annotations

from pathlib import Path
from typing import Any


ROLE_SOURCE = "source"
ROLE_TEST = "test"
_TEST_DIRS = {"tests", "test", "__tests__"}
_KEY_FILE_BONUS = {
    "main.py": 8,
    "__main__.py": 8,
    "cli.py": 7,
    "server.py": 7,
    "http_proxy.py": 8,
    "project_router.py": 8,
    "config.py": 6,
    "dashboard.html": 6,
}
_NOISE_PATH_SEGMENTS = {
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
    "history",
    "snapshots",
}
_NOISE_FILE_SUFFIXES = {".log", ".pid", ".tmp", ".cache", ".val", ".pyc", ".pyo"}
_NOISE_FILE_NAMES = {".ds_store", "thumbs.db"}


def module_sort_key(module: dict[str, Any]) -> tuple[float, float, float]:
    tier = str(module.get("tier", "")).lower()
    module_id = str(module.get("id", "")).lower()
    desc = str(module.get("desc", "")).lower()
    is_testish = 1.0 if ("test" in module_id or "test" in desc or "benchmark" in desc) else 0.0
    core_rank = 0.0 if tier == "core" else 1.0
    return (core_rank, is_testish, -float(module.get("core_score", 0.0)))


def rank_source_files(
    modules: list[dict[str, Any]],
    files: dict[str, dict],
    file_roles: dict[str, str],
) -> list[tuple[str, dict, float]]:
    module_scores = {
        module.get("id", ""): float(module.get("core_score", 0.0))
        for module in modules
    }
    ranked: list[tuple[str, dict, float]] = []
    for file_path, file_data in files.items():
        score = _score_source_file(file_path, file_data, file_roles, module_scores)
        if score > 0:
            ranked.append((file_path, file_data, score))
    ranked.sort(
        key=lambda item: (item[2], len(item[1].get("signatures", [])), item[0]),
        reverse=True,
    )
    return ranked


def _score_source_file(
    file_path: str,
    file_data: dict,
    file_roles: dict[str, str],
    module_scores: dict[str, float],
) -> float:
    if file_roles.get(file_path) != ROLE_SOURCE or is_noise_file_path(file_path):
        return 0.0
    parts = split_path(file_path)
    name = Path(file_path).name.lower()
    path_lower = file_path.lower()

    score = 0.0
    score += _src_path_bonus(path_lower)
    score += _marker_path_bonus(path_lower)
    score += float(_KEY_FILE_BONUS.get(name, 0))
    if "config" in name:
        score += 2.0
    score += module_scores.get(file_data.get("module", ""), 0.0) * 5.0
    if file_data.get("desc"):
        score += 1.5
    score += min(len(file_data.get("signatures", [])), 40) * 0.25
    if _is_testish_file(name, parts):
        score -= 12.0
    return score


def _src_path_bonus(path_lower: str) -> float:
    return 6.0 if "/src/" in path_lower or path_lower.startswith("src/") else 0.0


def _marker_path_bonus(path_lower: str) -> float:
    markers = ("/gateway/", "/router", "/server", "/nav/", "/memory/", "/mcp/")
    return 3.0 if any(marker in path_lower for marker in markers) else 0.0


def _is_testish_file(name: str, parts: tuple[str, ...]) -> bool:
    return "test" in name or any(part.lower() in _TEST_DIRS for part in parts)


def rank_test_files(files: dict[str, dict], file_roles: dict[str, str]) -> list[tuple[str, dict]]:
    ranked: list[tuple[str, dict]] = []
    for file_path, file_data in files.items():
        if file_roles.get(file_path) != ROLE_TEST:
            continue
        if is_noise_file_path(file_path):
            continue
        if "/vendor/" in file_path.lower() or file_path.lower().startswith("vendor/"):
            continue
        ranked.append((file_path, file_data))
    ranked.sort(key=lambda item: (len(item[1].get("signatures", [])), item[0]), reverse=True)
    return ranked


def split_path(path: str) -> tuple[str, ...]:
    return tuple(part for part in Path(path).as_posix().split("/") if part and part != ".")


def is_noise_file_path(file_path: str) -> bool:
    parts = split_path(file_path)
    if not parts:
        return False
    lower_parts = [part.lower() for part in parts]
    if any(part in _NOISE_PATH_SEGMENTS for part in lower_parts):
        return True

    name = parts[-1].lower()
    if name in _NOISE_FILE_NAMES:
        return True
    return any(name.endswith(suffix) for suffix in _NOISE_FILE_SUFFIXES)
