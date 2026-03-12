"""Deterministic architecture rules for hippocampus index."""

from __future__ import annotations

from statistics import median

from .architect_rule_support import (
    build_fan_in,
    is_zombie_file,
    iter_core_score_anomalies,
    iter_cycles,
    iter_layer_violations,
)
from .architect_models import RuleFinding, Severity


class RuleEngine:
    """Run deterministic architecture rules against the hippocampus index."""

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
        for violation in iter_layer_violations(self.module_deps, self._mod_by_id):
            src_id = violation["source"]
            tgt_id = violation["target"]
            findings.append(
                RuleFinding(
                    rule_id="layer-violation",
                    severity=Severity.CRITICAL,
                    message=f"Core module {src_id} depends on peripheral module {tgt_id}",
                    details=violation,
                )
            )
        return findings

    def _rule_circular_dependency(self) -> list[RuleFinding]:
        findings = []
        for cycle in iter_cycles(self.module_deps):
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
        fan_in = build_fan_in(self.file_deps)
        for anomaly in iter_core_score_anomalies(fan_in, self.files, self._mod_by_id):
            findings.append(
                RuleFinding(
                    rule_id="core-score-anomaly",
                    severity=Severity.WARNING,
                    message=(
                        f"File {anomaly['file']} has high fan-in ({anomaly['fan_in']}) "
                        f"but is in peripheral module {anomaly['module']}"
                    ),
                    details=anomaly,
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
        fan_in = build_fan_in(self.file_deps)
        zombies = [
            path
            for path, finfo in self.files.items()
            if is_zombie_file(path, finfo, fan_in=fan_in, mod_by_id=self._mod_by_id)
        ]

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
