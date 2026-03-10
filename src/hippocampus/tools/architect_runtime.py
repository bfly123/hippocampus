"""Public architect entrypoints."""

from __future__ import annotations

from pathlib import Path

from ..config import HippoConfig
from ..constants import ARCHITECT_REPORT_FILE
from ..utils import write_json
from .architect_llm import LLMAnalyzer
from .architect_models import ArchitectReport
from .architect_rules import RuleEngine
from .architect_runtime_helpers import compute_rule_score, load_index


async def run_architect_audit(
    output_dir: Path,
    config: HippoConfig,
    rules_only: bool = False,
    verbose: bool = False,
) -> dict:
    """Run architecture audit: rules + optional LLM analysis."""
    index = load_index(output_dir)
    engine = RuleEngine(index)
    findings = engine.run_all()
    rule_score = compute_rule_score(findings)
    report = ArchitectReport(mode="audit", rule_findings=findings, score=rule_score)

    if not rules_only:
        try:
            analyzer = LLMAnalyzer(config)
            llm_result = await analyzer.audit(index, findings)
            report.llm_analysis = llm_result
            llm_score = llm_result.get("health_score", rule_score)
            report.score = (rule_score + llm_score) // 2
        except Exception as exc:
            report.llm_analysis = {"error": str(exc)}
            if verbose:
                import sys

                print(f"LLM analysis failed: {exc}", file=sys.stderr)

    report_path = output_dir / ARCHITECT_REPORT_FILE
    write_json(report_path, report.to_dict())
    return report.to_dict()


async def run_architect_review(
    output_dir: Path,
    config: HippoConfig,
    num_commits: int = 5,
    verbose: bool = False,
) -> dict:
    """Review recent commits for architectural impact."""
    if num_commits < 1:
        raise ValueError("num_commits must be >= 1")

    index = load_index(output_dir)
    repo_root = output_dir.parent
    engine = RuleEngine(index)
    findings = engine.run_all()
    rule_score = compute_rule_score(findings)
    report = ArchitectReport(mode="review", rule_findings=findings, score=rule_score)

    try:
        analyzer = LLMAnalyzer(config)
        llm_result = await analyzer.review_commits(
            index,
            findings,
            num_commits,
            repo_root=repo_root,
        )
        report.llm_analysis = llm_result
    except Exception as exc:
        report.llm_analysis = {"error": str(exc)}
        if verbose:
            import sys

            print(f"LLM analysis failed: {exc}", file=sys.stderr)

    report_path = output_dir / ARCHITECT_REPORT_FILE
    write_json(report_path, report.to_dict())
    return report.to_dict()


async def run_architect_plan(
    output_dir: Path,
    config: HippoConfig,
    description: str,
    verbose: bool = False,
) -> dict:
    """Plan feature placement using LLM."""
    index = load_index(output_dir)
    report = ArchitectReport(mode="plan")

    try:
        analyzer = LLMAnalyzer(config)
        llm_result = await analyzer.plan_feature(index, description)
        report.llm_analysis = llm_result
    except Exception as exc:
        report.llm_analysis = {"error": str(exc)}
        if verbose:
            import sys

            print(f"LLM analysis failed: {exc}", file=sys.stderr)

    report.score = -1
    report_path = output_dir / ARCHITECT_REPORT_FILE
    write_json(report_path, report.to_dict())
    return report.to_dict()
