"""Deterministic architecture rules for hippocampus index."""

from __future__ import annotations

from pathlib import Path
from statistics import median
from typing import Any

from .architect_models import RuleFinding, Severity


class RuleEngine:
    """Run deterministic architecture rules against the hippocampus index."""

    _TIER_RANK = {"core": 0, "secondary": 1, "peripheral": 2}
    _NON_CODE_EXTS = frozenset(
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

    def __init__(self, index: dict):
        self.index = index
        self.modules: list[dict] = index.get("modules", [])
        self.files: dict[str, dict] = index.get("files", {})
        self.module_deps: dict[str, list[dict]] = index.get("module_dependencies", {})
        self.file_deps: dict[str, list[str]] = index.get("file_dependencies", {})
        self._mod_by_id: dict[str, dict] = {m["id"]: m for m in self.modules}

    def run_all(self) -> list[RuleFinding]:
        findings: list[RuleFinding] = []
        for name in sorted(dir(self)):
            if name.startswith("_rule_") and callable(getattr(self, name)):
                findings.extend(getattr(self, name)())
        return findings

    def _rule_layer_violation(self) -> list[RuleFinding]:
        findings = []
        for src_id, deps in self.module_deps.items():
            src_mod = self._mod_by_id.get(src_id)
            if not src_mod:
                continue
            if src_mod.get("role") == "interface":
                continue
            src_tier = src_mod.get("tier", "peripheral")
            for dep in deps:
                tgt_id = dep["target"]
                tgt_mod = self._mod_by_id.get(tgt_id)
                if not tgt_mod:
                    continue
                tgt_tier = tgt_mod.get("tier", "peripheral")
                src_rank = self._TIER_RANK.get(src_tier, 2)
                tgt_rank = self._TIER_RANK.get(tgt_tier, 2)
                if src_rank < tgt_rank and src_tier == "core" and tgt_tier == "peripheral":
                    findings.append(
                        RuleFinding(
                            rule_id="layer-violation",
                            severity=Severity.CRITICAL,
                            message=f"Core module {src_id} depends on peripheral module {tgt_id}",
                            details={
                                "source": src_id,
                                "target": tgt_id,
                                "source_tier": src_tier,
                                "target_tier": tgt_tier,
                                "files": dep.get("files", []),
                            },
                        )
                    )
        return findings

    def _rule_circular_dependency(self) -> list[RuleFinding]:
        findings = []
        adj: dict[str, list[str]] = {}
        for src_id, deps in self.module_deps.items():
            adj[src_id] = [d["target"] for d in deps if d["target"] != src_id]

        visited: set[str] = set()
        on_stack: set[str] = set()
        cycles_found: set[tuple[str, ...]] = set()

        def dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            on_stack.add(node)
            path.append(node)
            for neighbor in adj.get(node, []):
                if neighbor in on_stack:
                    cycle_start = path.index(neighbor)
                    cycle_nodes = path[cycle_start:]
                    min_val = min(cycle_nodes)
                    min_idx = cycle_nodes.index(min_val)
                    rotated = cycle_nodes[min_idx:] + cycle_nodes[:min_idx]
                    cycles_found.add(tuple(rotated))
                elif neighbor not in visited:
                    dfs(neighbor, path)
            path.pop()
            on_stack.discard(node)

        all_nodes = set(adj.keys())
        for deps in adj.values():
            all_nodes.update(deps)
        for node in sorted(all_nodes):
            if node not in visited:
                dfs(node, [])

        for cycle in sorted(cycles_found):
            display = list(cycle) + [cycle[0]]
            findings.append(
                RuleFinding(
                    rule_id="circular-dependency",
                    severity=Severity.WARNING,
                    message=f"Circular dependency: {' -> '.join(display)}",
                    details={"cycle": list(cycle)},
                )
            )
        return findings

    def _rule_core_score_anomaly(self) -> list[RuleFinding]:
        findings = []
        fan_in: dict[str, int] = {}
        for deps in self.file_deps.values():
            for target in deps:
                fan_in[target] = fan_in.get(target, 0) + 1

        for path, count in fan_in.items():
            if count < 5:
                continue
            finfo = self.files.get(path)
            if not finfo:
                continue
            mod_id = finfo.get("module")
            if not mod_id:
                continue
            mod = self._mod_by_id.get(mod_id)
            if not mod:
                continue
            if mod.get("tier") == "peripheral":
                findings.append(
                    RuleFinding(
                        rule_id="core-score-anomaly",
                        severity=Severity.WARNING,
                        message=(
                            f"File {path} has high fan-in ({count}) "
                            f"but is in peripheral module {mod_id}"
                        ),
                        details={
                            "file": path,
                            "fan_in": count,
                            "module": mod_id,
                            "tier": "peripheral",
                        },
                    )
                )
        return findings

    def _rule_high_fan_out(self) -> list[RuleFinding]:
        findings = []
        for mod_id, deps in self.module_deps.items():
            if len(deps) >= 6:
                targets = [d["target"] for d in deps]
                findings.append(
                    RuleFinding(
                        rule_id="high-fan-out",
                        severity=Severity.INFO,
                        message=f"Module {mod_id} has high fan-out ({len(deps)} dependencies)",
                        details={"module": mod_id, "out_degree": len(deps), "targets": targets},
                    )
                )
        return findings

    def _rule_orphan_files(self) -> list[RuleFinding]:
        findings = []
        orphans = []
        for path, finfo in self.files.items():
            if not finfo.get("module"):
                orphans.append(path)
        if orphans:
            findings.append(
                RuleFinding(
                    rule_id="orphan-files",
                    severity=Severity.INFO,
                    message=f"{len(orphans)} file(s) not assigned to any module",
                    details={"files": orphans[:20]},
                )
            )
        return findings

    def _rule_size_imbalance(self) -> list[RuleFinding]:
        findings = []
        counts = [m.get("file_count", 0) for m in self.modules]
        if not counts:
            return findings
        med = median(counts)
        threshold = max(med * 3, 15)
        for mod in self.modules:
            fc = mod.get("file_count", 0)
            if fc >= threshold:
                findings.append(
                    RuleFinding(
                        rule_id="size-imbalance",
                        severity=Severity.WARNING,
                        message=(
                            f"Module {mod['id']} has {fc} files "
                            f"(median={med:.0f}, threshold={threshold:.0f})"
                        ),
                        details={
                            "module": mod["id"],
                            "file_count": fc,
                            "median": med,
                            "threshold": threshold,
                        },
                    )
                )
        return findings

    def _rule_zombie_code(self) -> list[RuleFinding]:
        findings = []
        fan_in: dict[str, int] = {}
        for deps in self.file_deps.values():
            for target in deps:
                fan_in[target] = fan_in.get(target, 0) + 1

        entry_names = {"cli.py", "__main__.py", "__init__.py", "conftest.py", "setup.py"}
        zombies = []
        for path, finfo in self.files.items():
            ext = Path(path).suffix.lower()
            if ext in self._NON_CODE_EXTS or not ext:
                continue
            name = finfo.get("name", Path(path).name)
            if name in entry_names:
                continue
            if name.startswith("test_") or name.endswith("_test.py"):
                continue
            if fan_in.get(path, 0) == 0:
                mod_id = finfo.get("module")
                mod = self._mod_by_id.get(mod_id) if mod_id else None
                core_score = mod.get("core_score", 0) if mod else 0
                if core_score < 0.1:
                    zombies.append(path)

        if zombies:
            findings.append(
                RuleFinding(
                    rule_id="zombie-code",
                    severity=Severity.INFO,
                    message=f"{len(zombies)} file(s) with zero fan-in and low core_score",
                    details={"files": zombies[:20]},
                )
            )
        return findings
