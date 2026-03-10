from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .structure_prompt_project_map_paths import split_path


def rank_code_areas(
    files: dict[str, dict],
    file_roles: dict[str, str],
) -> list[tuple[str, int]]:
    buckets: Counter[str] = Counter()
    for fp in files:
        if file_roles.get(fp) != "source":
            continue
        parts = split_path(fp)
        if not parts:
            continue
        if len(parts) == 1:
            buckets["."] += 1
            continue
        buckets[parts[0]] += 1
        if len(parts) >= 2:
            buckets["/".join(parts[:2])] += 1

    scored = [(path, count) for path, count in buckets.items() if path != "." and count >= 2]
    scored.sort(key=lambda item: (item[1], item[0]), reverse=True)
    return scored[:8]


def collect_project_boundaries(
    files: dict[str, dict],
    file_roles: dict[str, str],
    entry_files: list[tuple[str, str, float]],
) -> list[dict[str, Any]]:
    boundary_data: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"source_files": 0, "test_files": 0, "core_areas": set()}
    )
    entry_by_root: dict[str, str] = {}

    for fp in files:
        parts = split_path(fp)
        if not parts:
            continue
        root = parts[0]
        bucket = boundary_data[root]
        role = file_roles.get(fp, "")
        if role == "source":
            bucket["source_files"] += 1
            if len(parts) >= 2:
                bucket["core_areas"].add("/".join(parts[:2]))
        elif role == "test":
            bucket["test_files"] += 1

    for fp, _reason, _score in entry_files:
        parts = split_path(fp)
        if parts:
            entry_by_root.setdefault(parts[0], fp)

    boundaries: list[dict[str, Any]] = []
    for root, bucket in boundary_data.items():
        if bucket["source_files"] == 0:
            continue
        boundaries.append(
            {
                "project": root,
                "source_files": bucket["source_files"],
                "test_files": bucket["test_files"],
                "entry": entry_by_root.get(root, ""),
                "core_areas": sorted(bucket["core_areas"])[:2],
            }
        )

    boundaries.sort(
        key=lambda item: (1 if item["entry"] else 0, item["source_files"], item["test_files"], item["project"]),
        reverse=True,
    )
    return boundaries[:8]
