from __future__ import annotations

import click

_SEV_ICON = {"critical": "[CRIT]", "warning": "[WARN]", "info": "[INFO]"}


def _print_rule_state(findings: list[dict]) -> None:
    crit = sum(1 for finding in findings if finding["severity"] == "critical")
    warn = sum(1 for finding in findings if finding["severity"] == "warning")
    click.echo(f"Current rule state: {crit} critical, {warn} warnings")


def _print_commit_assessments(assessments: list[dict]) -> None:
    if not assessments:
        return
    click.echo("\nCommit assessments:")
    for assessment in assessments:
        impact = assessment.get("impact", "?")
        tag = {"positive": "+", "neutral": "~", "negative": "-"}.get(impact, "?")
        click.echo(f"  [{tag}] {assessment.get('commit', '?')}")
        if assessment.get("notes"):
            click.echo(f"      {assessment['notes']}")


def _print_plan_entries(title: str, marker: str, items: list[dict], field: str) -> None:
    if not items:
        return
    click.echo(f"\n{title}:")
    for item in items:
        click.echo(f"  {marker} {item.get('path', '?')} — {item.get(field, '')}")


def _print_plan_lines(title: str, prefix: str, values: list[str]) -> None:
    if not values:
        return
    click.echo(f"\n{title}:")
    for value in values:
        click.echo(f"  {prefix} {value}")


def _print_findings(findings: list[dict]) -> None:
    click.echo(f"\nRule findings ({len(findings)}):")
    for finding in findings:
        icon = _SEV_ICON.get(finding["severity"], "[???]")
        click.echo(f"  {icon} {finding['rule_id']}: {finding['message']}")


def _print_llm_assessment(llm: dict, *, quiet: bool) -> None:
    if not llm:
        return
    if "error" in llm:
        if not quiet:
            click.echo(f"\nLLM analysis unavailable: {llm['error']}")
        return
    click.echo(f"\nLLM Assessment: {llm.get('summary', '')}")
    recommendations = llm.get("recommendations", [])
    if recommendations:
        click.echo("Recommendations:")
        for recommendation in recommendations[:5]:
            click.echo(
                f"  [{recommendation.get('priority', '?')}] "
                f"{recommendation.get('action', '')}"
            )


def print_audit_report(report: dict, quiet: bool) -> None:
    score = report.get("score", "?")
    click.echo(f"\nArchitecture Score: {score}/100")
    findings = report.get("rule_findings", [])
    if findings:
        _print_findings(findings)
    _print_llm_assessment(report.get("llm_analysis"), quiet=quiet)


def print_review_report(report: dict, quiet: bool) -> None:
    llm = report.get("llm_analysis", {})
    if llm.get("error"):
        if not quiet:
            click.echo(f"\nLLM analysis unavailable: {llm['error']}")
            findings = report.get("rule_findings", [])
            if findings:
                _print_rule_state(findings)
        return

    click.echo(f"\n{llm.get('summary', 'No summary available.')}")
    _print_commit_assessments(llm.get("commit_assessments", []))
    click.echo(f"\nOverall trend: {llm.get('overall_trend', '?')}")

    findings = report.get("rule_findings", [])
    if findings and not quiet:
        _print_rule_state(findings)


def _print_integration_seams(seams: list[dict]) -> None:
    if not seams:
        return
    click.echo("\nIntegration seams:")
    for seam in seams:
        click.echo(
            f"  {seam.get('file', '?')}:{seam.get('function', '?')} "
            f"— {seam.get('action', '')}"
        )


def _print_blast_radius(blast: list[str]) -> None:
    if not blast:
        return
    click.echo(f"\nImpact blast radius ({len(blast)} files):")
    for item in blast[:10]:
        click.echo(f"  {item}")
    if len(blast) > 10:
        click.echo(f"  ... and {len(blast) - 10} more")


def print_plan_report(report: dict, quiet: bool) -> None:
    llm = report.get("llm_analysis", {})
    if not llm:
        click.echo("No plan generated.")
        return
    if llm.get("error"):
        if not quiet:
            click.echo(f"\nLLM analysis unavailable: {llm['error']}")
        return

    click.echo(f"\nTarget module: {llm.get('target_module', '?')}")
    click.echo(f"Rationale: {llm.get('rationale', '')}")
    _print_plan_entries("Files to create", "+", llm.get("files_to_create", []), "purpose")
    _print_plan_entries("Files to modify", "~", llm.get("files_to_modify", []), "changes")
    _print_plan_lines("Risks", "-", llm.get("risks", []))
    _print_integration_seams(llm.get("integration_seams", []))
    _print_blast_radius(llm.get("impact_blast_radius", []))
