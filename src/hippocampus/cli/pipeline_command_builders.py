from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import click

from .pipeline_helpers import build_ranked_tag_report, run_pipeline_steps
from .target_compat import resolve_target_value, target_option_alias
from ..config import load_config, require_llm_configured
from ..constants import (
    CONFIG_FILE,
    HIPPO_DIR,
    PHASE1_CACHE_FILE,
    PHASE2_CACHE_FILE,
    PHASE3_CACHE_FILE,
)
from ..integration.bundle_state import write_bundle_state


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


def _clear_incremental_index_cache(output_dir: Path) -> list[Path]:
    cleared: list[Path] = []
    for cache_name in (PHASE1_CACHE_FILE, PHASE2_CACHE_FILE, PHASE3_CACHE_FILE):
        cache_path = output_dir / cache_name
        if cache_path.exists():
            cache_path.unlink()
            cleared.append(cache_path)
    return cleared


def build_repomap_command():
    @click.command("repomap")
    @click.option("--files", "-f", multiple=True, help="Files to analyze (repeatable).")
    @click.option("--limit", "-n", default=50, type=int, help="Max symbols to show.")
    @click.argument("target", required=False, default=".")
    @target_option_alias()
    @click.pass_context
    def repomap(ctx, target, target_option, files, limit):
        """Debug command: show Aider RepoMap symbol ranking."""
        target = resolve_target_value(target, target_option)
        tgt = Path(target).resolve()

        from ..tools.repomap_adapter import HippoRepoMap, check_repomap_available

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
    @click.option("--budget", default=10000, help="Token budget.")
    @click.option(
        "--ranking",
        type=click.Choice(["heuristic", "graph", "symbol"]),
        default="graph",
        help="Ranking method: heuristic (fast), graph (accurate), symbol (experimental).",
    )
    @click.option("--focus", multiple=True, help="Files to prioritize.")
    @click.argument("target", required=False, default=".")
    @target_option_alias()
    @click.pass_context
    def trim(ctx, target, target_option, budget, ranking, focus):
        """Dynamic trim with intelligent ranking."""
        target = resolve_target_value(target, target_option)
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR
        out.mkdir(parents=True, exist_ok=True)

        from ..tools.trimmer import run_trimmer

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
    @click.option("--phase", "phase_num", default=None, type=int, help="Run only this phase (0-4).")
    @click.option(
        "--no-llm",
        is_flag=True,
        hidden=True,
        help="Run only local phases and skip all LLM work.",
    )
    @click.argument("target", required=False, default=".")
    @target_option_alias()
    @click.pass_context
    def index(ctx, target, target_option, phase_num, no_llm):
        """Generate unified index -> hippocampus-index.json."""
        target = resolve_target_value(target, target_option)
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR
        out.mkdir(parents=True, exist_ok=True)

        from ..tools.index_gen import run_index_pipeline
        from ..tools.snapshot import save_snapshot

        cfg = _load_index_config(ctx, out)
        if not no_llm:
            _require_index_llm(cfg)
        _echo_index_start(ctx, phase_num=phase_num)

        result = asyncio.run(
            run_index_pipeline(
                tgt,
                out,
                cfg,
                phase=phase_num,
                verbose=ctx.obj["verbose"],
                show_progress=not ctx.obj["quiet"],
                no_llm=no_llm,
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
        write_bundle_state(tgt)
        try:
            snap = save_snapshot(out)
            if not ctx.obj["quiet"]:
                click.echo(f"Snapshot saved: {snap['snapshot_id']}")
        except FileNotFoundError:
            pass

    return index


def build_generate_command(*, command_refs: dict[str, object], run_cmd):
    @click.command("_generate", hidden=True)
    @click.argument("target", required=False, default=".")
    @target_option_alias()
    @click.option(
        "--prompt-profile",
        type=click.Choice(["auto", "map", "deep"]),
        default="map",
        show_default=True,
        help="Primary structure prompt profile for the initial pipeline run.",
    )
    @click.option(
        "--snapshot-message",
        "-m",
        default="generate",
        show_default=True,
        help="Snapshot message saved after the initial generation completes.",
    )
    @click.option(
        "--open-viz",
        is_flag=True,
        help="Open the generated visualization in a browser.",
    )
    @click.pass_context
    def generate(ctx, target, target_option, prompt_profile, snapshot_message, open_viz):
        """Full artifact generation, including architec-ready outputs."""
        target = resolve_target_value(target, target_option)
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR
        out.mkdir(parents=True, exist_ok=True)

        if not ctx.obj["quiet"]:
            click.echo("=== Step 1: Full Pipeline ===")
        ctx.invoke(run_cmd, target=target, prompt_profile=prompt_profile)

        if not ctx.obj["quiet"]:
            click.echo("=== Step 2: Generate Map + Deep Prompts ===")
        ctx.invoke(
            command_refs["structure-prompt-all"],
            target=target,
            set_default="keep",
        )
        write_bundle_state(tgt)

        if not ctx.obj["quiet"]:
            click.echo("=== Step 3: Save Snapshot ===")
        from ..tools.snapshot import save_snapshot

        snapshot = save_snapshot(out, message=snapshot_message)
        if not ctx.obj["quiet"]:
            click.echo(f"Snapshot saved: {snapshot['snapshot_id']}")

        if not ctx.obj["quiet"]:
            click.echo("=== Step 4: Generate Visualization ===")
        from ..viz.generator import generate_viz_html

        viz_path = generate_viz_html(out, verbose=ctx.obj["verbose"])
        if not ctx.obj["quiet"]:
            click.echo(f"Generated: {viz_path}")

        if open_viz:
            import webbrowser

            webbrowser.open(str(viz_path))

        if not ctx.obj["quiet"]:
            click.echo("=== Generation complete ===")

    return generate


def build_update_command(*, command_refs: dict[str, object], trim_cmd, index_cmd):
    @click.command("update")
    @click.option(
        "--default-prompt",
        type=click.Choice(["map", "deep", "keep"]),
        default="map",
        show_default=True,
        help="Which generated prompt becomes structure-prompt.md after refresh.",
    )
    @click.option(
        "--snapshot-message",
        "-m",
        default="update",
        show_default=True,
        help="Snapshot message saved after the refresh completes.",
    )
    @click.option(
        "--open-viz",
        is_flag=True,
        help="Open the generated visualization in a browser.",
    )
    @click.option(
        "--full",
        is_flag=True,
        help="Clear incremental caches before rebuilding from scratch.",
    )
    @click.option(
        "--no-llm",
        is_flag=True,
        hidden=True,
        help="Run only local phases and skip all LLM work.",
    )
    @click.argument("target", required=False, default=".")
    @target_option_alias()
    @click.pass_context
    def update(ctx, target, target_option, default_prompt, snapshot_message, open_viz, full, no_llm):
        """Incrementally refresh outputs, including architec-ready artifacts."""
        target = resolve_target_value(target, target_option)
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR
        out.mkdir(parents=True, exist_ok=True)

        if full:
            cleared = _clear_incremental_index_cache(out)
            if not ctx.obj["quiet"]:
                click.echo(
                    "Cleared incremental index cache: "
                    f"{len(cleared)} file(s)."
                )

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
                (
                    "Step 6: Index (incremental)",
                    index_cmd,
                    {"target": target, "phase_num": None, "no_llm": no_llm},
                ),
                (
                    "Step 7: Structure Prompt Bundle",
                    command_refs["structure-prompt-all"],
                    {
                        "target": target,
                        "set_default": default_prompt,
                        "llm_enhance": False if no_llm else None,
                    },
                ),
            ),
        )
        write_bundle_state(tgt)

        if not ctx.obj["quiet"]:
            click.echo("=== Step 8: Save Snapshot ===")
        from ..tools.snapshot import save_snapshot

        snapshot = save_snapshot(out, message=snapshot_message)
        if not ctx.obj["quiet"]:
            click.echo(f"Snapshot saved: {snapshot['snapshot_id']}")

        if not ctx.obj["quiet"]:
            click.echo("=== Step 9: Generate Visualization ===")
        from ..viz.generator import generate_viz_html

        viz_path = generate_viz_html(out, verbose=ctx.obj["verbose"])
        if not ctx.obj["quiet"]:
            click.echo(f"Generated: {viz_path}")

        if open_viz:
            import webbrowser

            webbrowser.open(str(viz_path))

        if not ctx.obj["quiet"]:
            click.echo("=== Update complete ===")

    return update


def build_refresh_command(*, update_cmd):
    @click.command("refresh")
    @click.argument("target", required=False, default=".")
    @target_option_alias()
    @click.option(
        "--default-prompt",
        type=click.Choice(["map", "deep", "keep"]),
        default="map",
        show_default=True,
        help="Which generated prompt becomes structure-prompt.md after refresh.",
    )
    @click.option(
        "--snapshot-message",
        "-m",
        default="refresh",
        show_default=True,
        help="Snapshot message saved after the refresh completes.",
    )
    @click.option(
        "--open-viz",
        is_flag=True,
        help="Open the generated visualization in a browser.",
    )
    @click.pass_context
    def refresh(ctx, target, target_option, default_prompt, snapshot_message, open_viz):
        """Force a full refresh by clearing incremental caches before rebuilding."""
        target = resolve_target_value(target, target_option)
        ctx.invoke(
            update_cmd,
            target=target,
            default_prompt=default_prompt,
            snapshot_message=snapshot_message,
            open_viz=open_viz,
            full=True,
            no_llm=False,
        )

    return refresh


def build_run_command(*, command_refs: dict[str, object], trim_cmd, index_cmd):
    @click.command("run")
    @click.option(
        "--prompt-profile",
        type=click.Choice(["auto", "map", "deep"]),
        default="map",
        show_default=True,
        help="Structure prompt profile for Step 7.",
    )
    @click.argument("target", required=False, default=".")
    @target_option_alias()
    @click.pass_context
    def run(ctx, target, target_option, prompt_profile):
        """Run full pipeline: init -> sig-extract -> tree -> index -> structure prompt."""
        target = resolve_target_value(target, target_option)
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
        write_bundle_state(tgt)

    return run
