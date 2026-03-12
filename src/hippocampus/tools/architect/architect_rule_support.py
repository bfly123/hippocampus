"""Support helpers for deterministic architecture rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

TIER_RANK = {"core": 0, "secondary": 1, "peripheral": 2}
NON_CODE_EXTS = frozenset(
    {
        ".md",
        ".txt",
        ".rst",
        ".adoc",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".cfg",
        ".ini",
        ".env",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".bat",
        ".ps1",
        ".html",
        ".css",
        ".svg",
        ".xml",
        ".xsl",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".webp",
        ".lock",
        ".sum",
        ".mod",
        ".scm",
    }
)


def build_fan_in(file_deps: dict[str, list[str]]) -> dict[str, int]:
    fan_in: dict[str, int] = {}
    for deps in file_deps.values():
        for target in deps:
            fan_in[target] = fan_in.get(target, 0) + 1
    return fan_in


def iter_cycles(module_deps: dict[str, list[dict[str, Any]]]) -> list[tuple[str, ...]]:
    adjacency = _build_adjacency(module_deps)
    visited: set[str] = set()
    on_stack: set[str] = set()
    cycles_found: set[tuple[str, ...]] = set()

    for node in _all_cycle_nodes(adjacency):
        if node not in visited:
            _walk_cycles(
                node,
                adjacency=adjacency,
                visited=visited,
                on_stack=on_stack,
                path=[],
                cycles_found=cycles_found,
            )
    return sorted(cycles_found)


def _build_adjacency(module_deps: dict[str, list[dict[str, Any]]]) -> dict[str, list[str]]:
    return {
        src_id: [dep["target"] for dep in deps if dep["target"] != src_id]
        for src_id, deps in module_deps.items()
    }


def _all_cycle_nodes(adjacency: dict[str, list[str]]) -> list[str]:
    nodes = set(adjacency)
    for deps in adjacency.values():
        nodes.update(deps)
    return sorted(nodes)


def _walk_cycles(
    node: str,
    *,
    adjacency: dict[str, list[str]],
    visited: set[str],
    on_stack: set[str],
    path: list[str],
    cycles_found: set[tuple[str, ...]],
) -> None:
    visited.add(node)
    on_stack.add(node)
    path.append(node)
    for neighbor in adjacency.get(node, []):
        if neighbor in on_stack:
            cycles_found.add(_normalize_cycle(path, neighbor))
            continue
        if neighbor not in visited:
            _walk_cycles(
                neighbor,
                adjacency=adjacency,
                visited=visited,
                on_stack=on_stack,
                path=path,
                cycles_found=cycles_found,
            )
    path.pop()
    on_stack.discard(node)


def _normalize_cycle(path: list[str], neighbor: str) -> tuple[str, ...]:
    cycle_start = path.index(neighbor)
    cycle_nodes = path[cycle_start:]
    min_value = min(cycle_nodes)
    min_index = cycle_nodes.index(min_value)
    rotated = cycle_nodes[min_index:] + cycle_nodes[:min_index]
    return tuple(rotated)


def is_non_code_candidate(path: str, finfo: dict[str, Any]) -> bool:
    ext = Path(path).suffix.lower()
    if ext in NON_CODE_EXTS or not ext:
        return False
    name = finfo.get("name", Path(path).name)
    return (
        name not in {"cli.py", "__main__.py", "__init__.py", "conftest.py", "setup.py"}
        and not name.startswith("test_")
        and not name.endswith("_test.py")
    )


def is_zombie_file(
    path: str,
    finfo: dict[str, Any],
    *,
    fan_in: dict[str, int],
    mod_by_id: dict[str, dict[str, Any]],
) -> bool:
    if fan_in.get(path, 0) != 0 or not is_non_code_candidate(path, finfo):
        return False
    mod_id = finfo.get("module")
    mod = mod_by_id.get(mod_id) if mod_id else None
    core_score = mod.get("core_score", 0) if mod else 0
    return core_score < 0.1


def iter_layer_violations(
    module_deps: dict[str, list[dict[str, Any]]],
    mod_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for src_id, deps in module_deps.items():
        src_mod = mod_by_id.get(src_id)
        if not src_mod or src_mod.get("role") == "interface":
            continue
        src_tier = src_mod.get("tier", "peripheral")
        for dep in deps:
            target = _build_layer_violation(src_id, src_tier, dep, mod_by_id)
            if target is not None:
                violations.append(target)
    return violations


def _build_layer_violation(
    src_id: str,
    src_tier: str,
    dep: dict[str, Any],
    mod_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    tgt_id = dep["target"]
    tgt_mod = mod_by_id.get(tgt_id)
    if not tgt_mod:
        return None
    tgt_tier = tgt_mod.get("tier", "peripheral")
    src_rank = TIER_RANK.get(src_tier, 2)
    tgt_rank = TIER_RANK.get(tgt_tier, 2)
    if src_rank < tgt_rank and src_tier == "core" and tgt_tier == "peripheral":
        return {
            "source": src_id,
            "target": tgt_id,
            "source_tier": src_tier,
            "target_tier": tgt_tier,
            "files": dep.get("files", []),
        }
    return None


def iter_core_score_anomalies(
    fan_in: dict[str, int],
    files: dict[str, dict[str, Any]],
    mod_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    for path, count in fan_in.items():
        if count < 5:
            continue
        anomaly = _build_core_score_anomaly(path, count, files, mod_by_id)
        if anomaly is not None:
            anomalies.append(anomaly)
    return anomalies


def _build_core_score_anomaly(
    path: str,
    count: int,
    files: dict[str, dict[str, Any]],
    mod_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    finfo = files.get(path)
    if not finfo:
        return None
    mod_id = finfo.get("module")
    if not mod_id:
        return None
    mod = mod_by_id.get(mod_id)
    if not mod or mod.get("tier") != "peripheral":
        return None
    return {
        "file": path,
        "fan_in": count,
        "module": mod_id,
        "tier": "peripheral",
    }
