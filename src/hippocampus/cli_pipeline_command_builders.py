from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import click

from .cli_pipeline_helpers import build_ranked_tag_report, run_pipeline_steps
from .config import load_config, require_llm_configured
from .constants import CONFIG_FILE, HIPPO_DIR


def _echo_index_start(ctx: Any, *, phase_num: int | None) -> None:
    if ctx.obj["quiet"]:
        return
    if phase_num is not None:
        click.echo(f"Running phase {phase_num} ...")
        return
    click.echo("Running full index pipeline ...")


def _load_index_config(ctx: Any, out: Path):
    cfg_path = Path(ctx.obj["config_path"]) if ctx.obj["config_path"] else out / CONFIG_FILE
    return load_config(cfg_path if cfg_path.exists() else None, project_root=out.parent)


def _require_index_llm(cfg) -> None:
    try:
        require_llm_configured(cfg)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc


def build_repomap_command():
    @click.command("repomap")
    @click.option("--target", default=".", help="Project root directory.")
    @click.option("--files", "-f", multiple=True, help="Files to analyze (repeatable).")
    @click.option("--limit", "-n", default=50, type=int, help="Max symbols to show.")
    @click.pass_context
    def repomap(ctx, target, files, limit):
        """Debug command: show Aider RepoMap symbol ranking."""
        tgt = Path(target).resolve()

        from .tools.repomap_adapter import HippoRepoMap, check_repomap_available

        available, error = check_repomap_available(tgt)
        if not available:
            click.echo("Error: RepoMap not available.")
            click.echo(f"  {error}")
            click.echo("\nInstall with: pip install -e '.[repomap]'")
            raise SystemExit(1)
        if not files:
            click.echo("Error: Provide at least one file with --files")
            raise SystemExit(1)

        try:
            repomap_obj = HippoRepoMap(root=tgt, map_tokens=2048, verbose=ctx.obj["verbose"])
            ranked_tags = repomap_obj.get_ranked_tags(
                chat_files=list(files),
                other_files=[],
                mentioned_files=set(),
                mentioned_idents=set(),
            )
            for line in build_ranked_tag_report(ranked_tags, limit=limit, file_count=len(files)):
                click.echo(line)
        except Exception as exc:
            click.echo(f"Error: {exc}")
            raise SystemExit(1)

    return repomap


def build_trim_command():
    @click.command("trim")
    @click.option("--target", default=".", help="Project root directory.")
    @click.option("--budget", default=10000, help="Token budget.")
    @click.option(
        "--ranking",
        type=click.Choice(["heuristic", "graph", "symbol"]),
        default="graph",
        help="Ranking method: heuristic (fast), graph (accurate), symbol (experimental).",
    )
    @click.option("--focus", multiple=True, help="Files to prioritize.")
    @click.pass_context
    def trim(ctx, target, budget, ranking, focus):
        """Dynamic trim with intelligent ranking."""
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR
        out.mkdir(parents=True, exist_ok=True)

        from .tools.trimmer import run_trimmer

        if not ctx.obj["quiet"]:
            click.echo(f"Trimming with budget {budget} ...")
            click.echo(f"  Ranking method: {ranking}")
            if focus:
                click.echo(f"  Focus on: {', '.join(focus)}")

        trimmed = run_trimmer(
            tgt,
            out,
            budget=budget,
            ranking_method=ranking,
            focus_files=list(focus) if focus else None,
            mentioned_files=None,
            verbose=ctx.obj["verbose"],
        )

        if not ctx.obj["quiet"]:
            click.echo(f"Done: {len(trimmed)} files included.")

    return trim


def build_index_command():
    @click.command("index")
    @click.option("--target", default=".", help="Project root directory.")
    @click.option("--phase", "phase_num", default=None, type=int, help="Run only this phase (0-4).")
    @click.pass_context
    def index(ctx, target, phase_num):
        """Generate unified index -> hippocampus-index.json."""
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR
        out.mkdir(parents=True, exist_ok=True)

        from .tools.index_gen import run_index_pipeline
        from .tools.snapshot import save_snapshot

        cfg = _load_index_config(ctx, out)
        _require_index_llm(cfg)
        _echo_index_start(ctx, phase_num=phase_num)

        result = asyncio.run(
            run_index_pipeline(
                tgt,
                out,
                cfg,
                phase=phase_num,
                verbose=ctx.obj["verbose"],
                no_llm=False,
            )
        )
        if result and not ctx.obj["quiet"]:
            stats = result.get("stats", {})
            click.echo(
                f"Done: {stats.get('total_files', 0)} files, "
                f"{stats.get('total_modules', 0)} modules."
            )
        if not result:
            return
        try:
            snap = save_snapshot(out)
            if not ctx.obj["quiet"]:
                click.echo(f"Snapshot saved: {snap['snapshot_id']}")
        except FileNotFoundError:
            pass

    return index


def build_run_command(*, command_refs: dict[str, object], trim_cmd, index_cmd):
    @click.command("run")
    @click.option("--target", default=".", help="Project root directory.")
    @click.option(
        "--prompt-profile",
        type=click.Choice(["auto", "map", "deep"]),
        default="map",
        show_default=True,
        help="Structure prompt profile for Step 7.",
    )
    @click.pass_context
    def run(ctx, target, prompt_profile):
        """Run full pipeline: init -> sig-extract -> tree -> index -> structure prompt."""
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR
        out.mkdir(parents=True, exist_ok=True)
        _require_index_llm(_load_index_config(ctx, out))
        run_pipeline_steps(
            ctx=ctx,
            quiet=ctx.obj["quiet"],
            echo=click.echo,
            steps=(
                ("Step 1: Init", command_refs["init"], {"target": target}),
                ("Step 2: Sig Extract", command_refs["sig-extract"], {"target": target}),
                ("Step 3: Tree", command_refs["tree"], {"target": target}),
                ("Step 4: Tree Diff", command_refs["tree-diff"], {"target": target}),
                ("Step 5: Trim", trim_cmd, {"target": target}),
                ("Step 6: Index", index_cmd, {"target": target}),
                (
                    f"Step 7: Structure Prompt ({prompt_profile} profile)",
                    command_refs["structure-prompt"],
                    {"target": target, "profile": prompt_profile},
                ),
            ),
        )

    return run
