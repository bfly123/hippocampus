from __future__ import annotations

import asyncio
import os
from pathlib import Path

import click

from ..constants import HIPPO_DIR, INDEX_FILE
from .target_compat import resolve_target_value, target_option_alias


def register_query_commands(cli) -> None:
    @cli.command("overview")
    @click.option("--budget", default=4000, type=int, help="Token budget.")
    @click.argument("target", required=False, default=".")
    @target_option_alias()
    @click.pass_context
    def overview(ctx, target, target_option, budget):
        """Render layered project overview from index."""
        target = resolve_target_value(target, target_option)
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR

        from ..query.overview import build_overview
        from ..utils import read_json

        index_path = out / INDEX_FILE
        if not index_path.exists():
            click.echo("Error: hippocampus-index.json not found. Run 'hippo index' first.")
            raise SystemExit(1)

        index = read_json(index_path)
        result = build_overview(index, budget=budget)
        click.echo(result["content"])
        if not ctx.obj["quiet"]:
            click.echo(
                f"---\nLayers: {', '.join(result['layers_included'])} | "
                f"Tokens: ~{result['consumed_tokens']}/{budget}"
            )

    @cli.command("expand")
    @click.argument("path")
    @click.option(
        "--level",
        default="L2",
        type=click.Choice(["L2", "L3"]),
        help="Expansion level.",
    )
    @click.option("--budget", default=2000, type=int, help="Token budget.")
    @click.argument("target", required=False, default=".")
    @target_option_alias()
    @click.pass_context
    def expand(ctx, path, target, target_option, level, budget):
        """Expand a module or path from the index."""
        target = resolve_target_value(target, target_option)
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR

        from ..query.expand import build_expand
        from ..utils import read_json

        index_path = out / INDEX_FILE
        if not index_path.exists():
            click.echo("Error: hippocampus-index.json not found. Run 'hippo index' first.")
            raise SystemExit(1)

        index = read_json(index_path)
        result = build_expand(index, path, level=level, budget=budget)
        click.echo(result["content"])
        if not ctx.obj["quiet"]:
            click.echo(
                f"---\nPath: {result['path']} | Level: {result['level']} | "
                f"Tokens: ~{result['consumed_tokens']}/{budget}"
            )

    @cli.command("search")
    @click.option("--tags", "-t", multiple=True, help="Tags to match (repeatable).")
    @click.option("--pattern", "-p", default=None, help="Substring pattern to search.")
    @click.option("--limit", "-n", default=10, type=int, help="Max results.")
    @click.argument("target", required=False, default=".")
    @target_option_alias()
    @click.pass_context
    def search(ctx, tags, pattern, limit, target, target_option):
        """Search indexed files by tags and/or keyword pattern."""
        target = resolve_target_value(target, target_option)
        if not tags and not pattern:
            click.echo("Error: provide at least --tags or --pattern.")
            raise SystemExit(1)

        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR

        from ..query.search import build_search
        from ..utils import read_json

        index_path = out / INDEX_FILE
        if not index_path.exists():
            click.echo("Error: hippocampus-index.json not found. Run 'hippo index' first.")
            raise SystemExit(1)

        index = read_json(index_path)
        result = build_search(index, tags=list(tags) if tags else None, pattern=pattern, limit=limit)
        click.echo(result["content"])
        if not ctx.obj["quiet"]:
            click.echo(
                f"---\nMatches: {len(result['matches'])} | "
                f"Tokens: ~{result['consumed_tokens']}"
            )

    @cli.command("review")
    @click.option(
        "--staged",
        is_flag=True,
        default=True,
        hidden=True,
        help="Review staged changes (default).",
    )
    @click.argument("target", required=False, default=".")
    @target_option_alias()
    @click.pass_context
    def review(ctx, staged, target, target_option):
        """Review staged changes against architecture."""
        target = resolve_target_value(target, target_option)
        if not staged:
            click.echo("Currently only --staged is supported.")
            return

        from ..tools.reviewer import Reviewer

        reviewer = Reviewer()
        tgt = Path(target).resolve()
        previous_cwd = Path.cwd()
        try:
            os.chdir(tgt)
            exit_code = asyncio.run(reviewer.review_staged())
        finally:
            os.chdir(previous_cwd)
        if exit_code != 0:
            ctx.exit(exit_code)


def register_viz_command(cli) -> None:
    @cli.command("viz")
    @click.option("--open", "open_browser", is_flag=True, help="Open in browser.")
    @click.argument("target", required=False, default=".")
    @target_option_alias()
    @click.pass_context
    def viz(ctx, target, target_option, open_browser):
        """Generate interactive HTML visualization."""
        target = resolve_target_value(target, target_option)
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR

        from ..viz.generator import generate_viz_html

        path = generate_viz_html(out, verbose=ctx.obj["verbose"])
        if not ctx.obj["quiet"]:
            click.echo(f"Generated: {path}")
        if open_browser:
            import webbrowser

            webbrowser.open(str(path))
