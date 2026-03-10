from __future__ import annotations

import click

_SEV_ICON = {"critical": "[CRIT]", "warning": "[WARN]", "info": "[INFO]"}


def print_audit_report(report: dict, quiet: bool) -> None:
    score = report.get("score", "?")
    click.echo(f"\nArchitecture Score: {score}/100")
    findings = report.get("rule_findings", [])
    if findings:
        click.echo(f"\nRule findings ({len(findings)}):")
        for finding in findings:
            icon = _SEV_ICON.get(finding["severity"], "[???]")
            click.echo(f"  {icon} {finding['rule_id']}: {finding['message']}")

    llm = report.get("llm_analysis")
    if llm and "error" not in llm:
        click.echo(f"\nLLM Assessment: {llm.get('summary', '')}")
        recs = llm.get("recommendations", [])
        if recs:
            click.echo("Recommendations:")
            for rec in recs[:5]:
                click.echo(f"  [{rec.get('priority', '?')}] {rec.get('action', '')}")
    elif llm and "error" in llm and not quiet:
        click.echo(f"\nLLM analysis unavailable: {llm['error']}")


def print_review_report(report: dict, quiet: bool) -> None:
    llm = report.get("llm_analysis", {})
    if llm.get("error"):
        if not quiet:
            click.echo(f"\nLLM analysis unavailable: {llm['error']}")
        findings = report.get("rule_findings", [])
        if findings and not quiet:
            crit = sum(1 for finding in findings if finding["severity"] == "critical")
            warn = sum(1 for finding in findings if finding["severity"] == "warning")
            click.echo(f"Current rule state: {crit} critical, {warn} warnings")
        return

    click.echo(f"\n{llm.get('summary', 'No summary available.')}")
    assessments = llm.get("commit_assessments", [])
    if assessments:
        click.echo("\nCommit assessments:")
        for assessment in assessments:
            impact = assessment.get("impact", "?")
            tag = {"positive": "+", "neutral": "~", "negative": "-"}.get(impact, "?")
            click.echo(f"  [{tag}] {assessment.get('commit', '?')}")
            if assessment.get("notes"):
                click.echo(f"      {assessment['notes']}")
    trend = llm.get("overall_trend", "?")
    click.echo(f"\nOverall trend: {trend}")

    findings = report.get("rule_findings", [])
    if findings and not quiet:
        crit = sum(1 for finding in findings if finding["severity"] == "critical")
        warn = sum(1 for finding in findings if finding["severity"] == "warning")
        click.echo(f"Current rule state: {crit} critical, {warn} warnings")


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
    creates = llm.get("files_to_create", [])
    if creates:
        click.echo("\nFiles to create:")
        for item in creates:
            click.echo(f"  + {item.get('path', '?')} — {item.get('purpose', '')}")
    modifies = llm.get("files_to_modify", [])
    if modifies:
        click.echo("\nFiles to modify:")
        for item in modifies:
            click.echo(f"  ~ {item.get('path', '?')} — {item.get('changes', '')}")
    risks = llm.get("risks", [])
    if risks:
        click.echo("\nRisks:")
        for risk in risks:
            click.echo(f"  - {risk}")
    seams = llm.get("integration_seams", [])
    if seams:
        click.echo("\nIntegration seams:")
        for seam in seams:
            click.echo(
                f"  {seam.get('file', '?')}:{seam.get('function', '?')} — {seam.get('action', '')}"
            )
    blast = llm.get("impact_blast_radius", [])
    if blast:
        click.echo(f"\nImpact blast radius ({len(blast)} files):")
        for item in blast[:10]:
            click.echo(f"  {item}")
        if len(blast) > 10:
            click.echo(f"  ... and {len(blast) - 10} more")
