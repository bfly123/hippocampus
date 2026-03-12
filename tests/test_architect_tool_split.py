from __future__ import annotations

from hippocampus.tools.architect import (
    LLMAnalyzer,
    RuleEngine,
    run_architect_audit,
    run_architect_plan,
    run_architect_review,
)


def test_architect_facade_exports_split_symbols() -> None:
    assert RuleEngine.__module__ == "hippocampus.tools.architect.architect_rules"
    assert LLMAnalyzer.__module__ == "hippocampus.tools.architect.architect_llm"
    assert run_architect_audit.__module__ == "hippocampus.tools.architect.architect_runtime"
    assert run_architect_review.__module__ == "hippocampus.tools.architect.architect_runtime"
    assert run_architect_plan.__module__ == "hippocampus.tools.architect.architect_runtime"


def test_rule_engine_still_runs_after_split() -> None:
    index = {
        "modules": [
            {"id": "a", "tier": "core", "role": "domain", "file_count": 1},
            {"id": "b", "tier": "peripheral", "role": "infra", "file_count": 1},
        ],
        "files": {},
        "module_dependencies": {"a": [{"target": "b", "weight": 1.0, "files": ["x.py"]}]},
        "file_dependencies": {},
    }
    findings = RuleEngine(index).run_all()
    assert any(item.rule_id == "layer-violation" for item in findings)
