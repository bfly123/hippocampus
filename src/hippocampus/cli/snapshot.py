from __future__ import annotations

from pathlib import Path

import click

from ..constants import HIPPO_DIR, INDEX_FILE


def _target_output_dir(target: str) -> Path:
    return Path(target).resolve() / HIPPO_DIR


def _print_quiet_footer(ctx, text: str) -> None:
    if not ctx.obj["quiet"]:
        click.echo(text)


def _raise_missing_index() -> None:
    click.echo("Error: hippocampus-index.json not found. Run 'hippo index' first.")
    raise SystemExit(1)


def _load_current_stats_index(out: Path):
    from ..utils import read_json

    index_path = out / INDEX_FILE
    if not index_path.exists():
        _raise_missing_index()
    return read_json(index_path)


def _render_stats_result(ctx, result: dict, footer: str | None = None) -> None:
    click.echo(result["content"])
    if footer:
        _print_quiet_footer(ctx, footer)


def _history_stats_result(out: Path):
    from ..query.stats import build_stats, build_stats_history
    from ..tools.snapshot import list_snapshots

    snapshots = list_snapshots(out)
    snapshots.reverse()
    if len(snapshots) < 2:
        result = build_stats(_load_current_stats_index(out))
        footer = "---\n(Need >=2 snapshots for history; showing current stats.)"
        return result, footer
    result = build_stats_history(snapshots)
    footer = (
        f"---\nSnapshots: {result['snapshots_count']} | "
        f"Tokens: ~{result['consumed_tokens']}"
    )
    return result, footer


def register_snapshot_commands(cli) -> click.Group:
    @cli.group("snapshot")
    @click.pass_context
    def snapshot_group(ctx):
        """Manage index snapshots."""
        pass

    @snapshot_group.command("save")
    @click.option("--message", "-m", default=None, help="Optional snapshot message.")
    @click.argument("target", required=False, default=".")
    @click.pass_context
    def snapshot_save(ctx, message, target):
        """Archive current index as a timestamped snapshot."""
        from ..tools.snapshot import save_snapshot

        try:
            result = save_snapshot(_target_output_dir(target), message=message)
        except FileNotFoundError:
            _raise_missing_index()
        _print_quiet_footer(ctx, f"Snapshot saved: {result['snapshot_id']}")

    @snapshot_group.command("list")
    @click.argument("target", required=False, default=".")
    @click.pass_context
    def snapshot_list(ctx, target):
        """List all archived snapshots."""
        del ctx
        from ..tools.snapshot import list_snapshots

        snapshots = list_snapshots(_target_output_dir(target))
        if not snapshots:
            click.echo("No snapshots found.")
            return
        for snapshot in snapshots:
            stats = snapshot.get("stats", {})
            message = f"  — {snapshot['message']}" if snapshot.get("message") else ""
            click.echo(
                f"{snapshot['snapshot_id']}  "
                f"files={stats.get('total_files', '?')} "
                f"modules={stats.get('total_modules', '?')}"
                f"{message}"
            )

    @snapshot_group.command("show")
    @click.argument("ref", default="latest")
    @click.option("--budget", default=4000, type=int, help="Token budget.")
    @click.argument("target", required=False, default=".")
    @click.pass_context
    def snapshot_show(ctx, ref, target, budget):
        """Show a snapshot as a project overview."""
        from ..query.overview import build_overview
        from ..tools.snapshot import resolve_snapshot

        out = _target_output_dir(target)
        try:
            index = resolve_snapshot(out, ref)
        except (FileNotFoundError, ValueError) as exc:
            click.echo(f"Error: {exc}")
            raise SystemExit(1)

        result = build_overview(index, budget=budget)
        click.echo(result["content"])
        _print_quiet_footer(
            ctx,
            f"---\nRef: {ref} | Tokens: ~{result['consumed_tokens']}/{budget}",
        )

    return snapshot_group


def register_history_commands(cli) -> None:
    @cli.command("diff")
    @click.argument("old_ref", default="latest~1")
    @click.argument("new_ref", default="latest")
    @click.argument("target", required=False, default=".")
    @click.pass_context
    def diff(ctx, old_ref, new_ref, target):
        """Compare two index versions."""
        from ..query.diff import build_diff
        from ..tools.snapshot import resolve_snapshot

        out = _target_output_dir(target)
        try:
            old_index = resolve_snapshot(out, old_ref)
            new_index = resolve_snapshot(out, new_ref)
        except (FileNotFoundError, ValueError) as exc:
            click.echo(f"Error: {exc}")
            raise SystemExit(1)

        result = build_diff(old_index, new_index, old_id=old_ref, new_id=new_ref)
        click.echo(result["content"])
        _print_quiet_footer(
            ctx,
            f"---\nChange magnitude: {result['change_magnitude']} | "
            f"Tokens: ~{result['consumed_tokens']}",
        )

    @cli.command("stats")
    @click.option("--history", is_flag=True, help="Show cross-version trends.")
    @click.argument("target", required=False, default=".")
    @click.pass_context
    def stats(ctx, history, target):
        """Show index statistics and optional history trends."""
        from ..query.stats import build_stats

        out = _target_output_dir(target)
        if history:
            result, footer = _history_stats_result(out)
            _render_stats_result(ctx, result, footer)
            return

        result = build_stats(_load_current_stats_index(out))
        footer = f"---\nModules: {len(result['modules'])} | Tokens: ~{result['consumed_tokens']}"
        _render_stats_result(ctx, result, footer)
