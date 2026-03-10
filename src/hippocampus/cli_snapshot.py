from __future__ import annotations

from pathlib import Path

import click

from .constants import HIPPO_DIR, INDEX_FILE


def register_snapshot_commands(cli) -> click.Group:
    @cli.group("snapshot")
    @click.pass_context
    def snapshot_group(ctx):
        """Manage index snapshots."""
        pass

    @snapshot_group.command("save")
    @click.option("--message", "-m", default=None, help="Optional snapshot message.")
    @click.option("--target", default=".", help="Project root directory.")
    @click.pass_context
    def snapshot_save(ctx, message, target):
        """Archive current index as a timestamped snapshot."""
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR

        from .tools.snapshot import save_snapshot

        try:
            result = save_snapshot(out, message=message)
        except FileNotFoundError:
            click.echo("Error: hippocampus-index.json not found. Run 'hippo index' first.")
            raise SystemExit(1)

        if not ctx.obj["quiet"]:
            click.echo(f"Snapshot saved: {result['snapshot_id']}")

    @snapshot_group.command("list")
    @click.option("--target", default=".", help="Project root directory.")
    @click.pass_context
    def snapshot_list(ctx, target):
        """List all archived snapshots."""
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR

        from .tools.snapshot import list_snapshots

        snaps = list_snapshots(out)
        if not snaps:
            click.echo("No snapshots found.")
            return

        for snap in snaps:
            stats = snap.get("stats", {})
            message = f"  — {snap['message']}" if snap.get("message") else ""
            click.echo(
                f"{snap['snapshot_id']}  "
                f"files={stats.get('total_files', '?')} "
                f"modules={stats.get('total_modules', '?')}"
                f"{message}"
            )

    @snapshot_group.command("show")
    @click.argument("ref", default="latest")
    @click.option("--target", default=".", help="Project root directory.")
    @click.option("--budget", default=4000, type=int, help="Token budget.")
    @click.pass_context
    def snapshot_show(ctx, ref, target, budget):
        """Show a snapshot as a project overview."""
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR

        from .query.overview import build_overview
        from .tools.snapshot import resolve_snapshot

        try:
            index = resolve_snapshot(out, ref)
        except (FileNotFoundError, ValueError) as exc:
            click.echo(f"Error: {exc}")
            raise SystemExit(1)

        result = build_overview(index, budget=budget)
        click.echo(result["content"])
        if not ctx.obj["quiet"]:
            click.echo(
                f"---\nRef: {ref} | "
                f"Tokens: ~{result['consumed_tokens']}/{budget}"
            )

    return snapshot_group


def register_history_commands(cli) -> None:
    @cli.command("diff")
    @click.argument("old_ref", default="latest~1")
    @click.argument("new_ref", default="latest")
    @click.option("--target", default=".", help="Project root directory.")
    @click.pass_context
    def diff(ctx, old_ref, new_ref, target):
        """Compare two index versions."""
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR

        from .query.diff import build_diff
        from .tools.snapshot import resolve_snapshot

        try:
            old_index = resolve_snapshot(out, old_ref)
            new_index = resolve_snapshot(out, new_ref)
        except (FileNotFoundError, ValueError) as exc:
            click.echo(f"Error: {exc}")
            raise SystemExit(1)

        result = build_diff(old_index, new_index, old_id=old_ref, new_id=new_ref)
        click.echo(result["content"])
        if not ctx.obj["quiet"]:
            click.echo(
                f"---\nChange magnitude: {result['change_magnitude']} | "
                f"Tokens: ~{result['consumed_tokens']}"
            )

    @cli.command("stats")
    @click.option("--history", is_flag=True, help="Show cross-version trends.")
    @click.option("--target", default=".", help="Project root directory.")
    @click.pass_context
    def stats(ctx, history, target):
        """Show index statistics and optional history trends."""
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR

        from .utils import read_json

        if history:
            from .query.stats import build_stats, build_stats_history
            from .tools.snapshot import list_snapshots

            snaps = list_snapshots(out)
            snaps.reverse()

            if len(snaps) < 2:
                index_path = out / INDEX_FILE
                if not index_path.exists():
                    click.echo(
                        "Error: hippocampus-index.json not found. "
                        "Run 'hippo index' first."
                    )
                    raise SystemExit(1)
                index = read_json(index_path)
                result = build_stats(index)
                click.echo(result["content"])
                if not ctx.obj["quiet"]:
                    click.echo(
                        "---\n(Need >=2 snapshots for history; "
                        "showing current stats.)"
                    )
                return

            result = build_stats_history(snaps)
            click.echo(result["content"])
            if not ctx.obj["quiet"]:
                click.echo(
                    f"---\nSnapshots: {result['snapshots_count']} | "
                    f"Tokens: ~{result['consumed_tokens']}"
                )
            return

        from .query.stats import build_stats

        index_path = out / INDEX_FILE
        if not index_path.exists():
            click.echo(
                "Error: hippocampus-index.json not found. "
                "Run 'hippo index' first."
            )
            raise SystemExit(1)

        index = read_json(index_path)
        result = build_stats(index)
        click.echo(result["content"])
        if not ctx.obj["quiet"]:
            click.echo(
                f"---\nModules: {len(result['modules'])} | "
                f"Tokens: ~{result['consumed_tokens']}"
            )
