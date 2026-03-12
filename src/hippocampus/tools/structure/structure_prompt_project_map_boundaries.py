from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .structure_prompt_project_map_paths import split_path


def rank_code_areas(
    files: dict[str, dict],
    file_roles: dict[str, str],
) -> list[tuple[str, int]]:
    buckets: Counter[str] = Counter()
    for file_path in files:
        _add_code_area_counts(buckets, file_path, file_roles)
    scored = [(path, count) for path, count in buckets.items() if path != "." and count >= 2]
    scored.sort(key=lambda item: (item[1], item[0]), reverse=True)
    return scored[:8]


def _add_code_area_counts(
    buckets: Counter[str],
    file_path: str,
    file_roles: dict[str, str],
) -> None:
    if file_roles.get(file_path) != "source":
        return
    parts = split_path(file_path)
    if not parts:
        return
    if len(parts) == 1:
        buckets["."] += 1
        return
    buckets[parts[0]] += 1
    if len(parts) >= 2:
        buckets["/".join(parts[:2])] += 1


def collect_project_boundaries(
    files: dict[str, dict],
    file_roles: dict[str, str],
    entry_files: list[tuple[str, str, float]],
) -> list[dict[str, Any]]:
    boundary_data: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"source_files": 0, "test_files": 0, "core_areas": set()}
    )
    entry_by_root = _entry_files_by_root(entry_files)

    for file_path in files:
        _update_boundary_bucket(boundary_data, file_path, file_roles)

    boundaries = [
        _build_boundary_item(root, bucket, entry_by_root)
        for root, bucket in boundary_data.items()
        if bucket["source_files"] > 0
    ]
    boundaries.sort(key=_boundary_sort_key, reverse=True)
    return boundaries[:8]


def _entry_files_by_root(entry_files: list[tuple[str, str, float]]) -> dict[str, str]:
    entry_by_root: dict[str, str] = {}
    for file_path, _reason, _score in entry_files:
        parts = split_path(file_path)
        if parts:
            entry_by_root.setdefault(parts[0], file_path)
    return entry_by_root


def _update_boundary_bucket(
    boundary_data: dict[str, dict[str, Any]],
    file_path: str,
    file_roles: dict[str, str],
) -> None:
    parts = split_path(file_path)
    if not parts:
        return
    root = parts[0]
    bucket = boundary_data[root]
    role = file_roles.get(file_path, "")
    if role == "source":
        bucket["source_files"] += 1
        if len(parts) >= 2:
            bucket["core_areas"].add("/".join(parts[:2]))
    elif role == "test":
        bucket["test_files"] += 1


def _build_boundary_item(
    root: str,
    bucket: dict[str, Any],
    entry_by_root: dict[str, str],
) -> dict[str, Any]:
    return {
        "project": root,
        "source_files": bucket["source_files"],
        "test_files": bucket["test_files"],
        "entry": entry_by_root.get(root, ""),
        "core_areas": sorted(bucket["core_areas"])[:2],
    }


def _boundary_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        1 if item["entry"] else 0,
        item["source_files"],
        item["test_files"],
        item["project"],
    )
