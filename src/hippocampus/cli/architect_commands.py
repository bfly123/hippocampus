from __future__ import annotations

import asyncio
from pathlib import Path

import click

from .architect_reports import (
    print_audit_report,
    print_plan_report,
    print_review_report,
)
from ..config import load_config
from ..constants import CONFIG_FILE, HIPPO_DIR


def _resolve_out_and_config(ctx, target: str):
    tgt = Path(target).resolve()
    out = tgt / HIPPO_DIR
    cfg_path = Path(ctx.obj["config_path"]) if ctx.obj["config_path"] else out / CONFIG_FILE
    cfg = load_config(cfg_path if cfg_path.exists() else None, project_root=tgt)
    return out, cfg


def _run_architect_report(
    ctx,
    *,
    target: str,
    banner: str,
    error_types: tuple[type[Exception], ...],
    run_fn,
    run_kwargs: dict,
    report_printer,
) -> None:
    out, cfg = _resolve_out_and_config(ctx, target)
    if not ctx.obj["quiet"]:
        click.echo(banner)
    try:
        report = asyncio.run(run_fn(out, cfg, verbose=ctx.obj["verbose"], **run_kwargs))
    except error_types as exc:
        click.echo(f"Error: {exc}")
        raise SystemExit(1)
    report_printer(report, ctx.obj["quiet"])


def register_architect_audit_command(architect_group) -> None:
    @architect_group.command("audit")
    @click.option("--rules-only", is_flag=True, help="Skip LLM, run rule engine only.")
    @click.option("--target", default=".", help="Project root directory.")
    @click.pass_context
    def architect_audit(ctx, rules_only, target):
        """Run architecture health audit."""
        from ..tools.architect import run_architect_audit

        _run_architect_report(
            ctx,
            target=target,
            banner="Running architecture audit ...",
            error_types=(FileNotFoundError,),
            run_fn=run_architect_audit,
            run_kwargs={"rules_only": rules_only},
            report_printer=print_audit_report,
        )


def register_architect_review_command(architect_group) -> None:
    @architect_group.command("review")
    @click.option("-n", "num_commits", default=5, type=click.IntRange(min=1), help="Number of recent commits.")
    @click.option("--target", default=".", help="Project root directory.")
    @click.pass_context
    def architect_review(ctx, num_commits, target):
        """Review recent commits for architectural impact."""
        from ..tools.architect import run_architect_review

        _run_architect_report(
            ctx,
            target=target,
            banner=f"Reviewing last {num_commits} commits ...",
            error_types=(FileNotFoundError, ValueError),
            run_fn=run_architect_review,
            run_kwargs={"num_commits": num_commits},
            report_printer=print_review_report,
        )


def register_architect_plan_command(architect_group) -> None:
    @architect_group.command("plan")
    @click.argument("description")
    @click.option("--target", default=".", help="Project root directory.")
    @click.pass_context
    def architect_plan(ctx, description, target):
        """Plan feature placement in the architecture."""
        from ..tools.architect import run_architect_plan

        _run_architect_report(
            ctx,
            target=target,
            banner="Planning feature placement ...",
            error_types=(FileNotFoundError,),
            run_fn=run_architect_plan,
            run_kwargs={"description": description},
            report_printer=print_plan_report,
        )
