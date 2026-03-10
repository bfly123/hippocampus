"""Architect tool facade.

This module keeps backward-compatible exports while implementation is split into
focused modules for models, rules, LLM analysis, and runtime entrypoints.
"""

from __future__ import annotations

from .architect_llm import LLMAnalyzer
from .architect_models import ArchitectReport, RuleFinding, Severity
from .architect_rules import RuleEngine
from .architect_runtime import (
    run_architect_audit,
    run_architect_plan,
    run_architect_review,
)

__all__ = [
    "Severity",
    "RuleFinding",
    "ArchitectReport",
    "RuleEngine",
    "LLMAnalyzer",
    "run_architect_audit",
    "run_architect_review",
    "run_architect_plan",
]
