"""Data models for architect tooling."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class RuleFinding:
    rule_id: str
    severity: Severity
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArchitectReport:
    mode: str
    rule_findings: list[RuleFinding] = field(default_factory=list)
    llm_analysis: Optional[dict] = None
    score: int = 100

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "score": self.score,
            "rule_findings": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity.value,
                    "message": f.message,
                    "details": f.details,
                }
                for f in self.rule_findings
            ],
            "llm_analysis": self.llm_analysis,
        }
