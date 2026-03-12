"""Click CLI entry point — hippo command group."""

from __future__ import annotations

import click
from click.formatting import HelpFormatter

from .commands_core import register_core_commands
from .query import register_query_commands, register_viz_command
from .snapshot import register_history_commands, register_snapshot_commands


class HippocampusGroup(click.Group):
    """CLI group that renders top-level commands in curated sections."""

    COMMAND_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "Core Workflow",
            (
                "onekey",
                "update",
                "init",
                "sig-extract",
                "tree",
                "index",
                "structure-prompt",
                "viz",
            ),
        ),
        (
            "Explore & Inspect",
            (
                "overview",
                "search",
                "expand",
                "snapshot",
                "diff",
                "stats",
            ),
        ),
        (
            "Advanced Tools",
            (
                "run",
                "trim",
                "tree-diff",
                "repomap",
                "review",
                "structure-prompt-all",
            ),
        ),
    )

    def format_commands(self, ctx: click.Context, formatter: HelpFormatter) -> None:
        rows_by_section: list[tuple[str, list[tuple[str, str]]]] = []
        seen: set[str] = set()

        for section_name, command_names in self.COMMAND_SECTIONS:
            rows: list[tuple[str, str]] = []
            for name in command_names:
                cmd = self.get_command(ctx, name)
                if cmd is None:
                    continue
                seen.add(name)
                rows.append((name, cmd.get_short_help_str(formatter.width)))
            if rows:
                rows_by_section.append((section_name, rows))

        remaining = [name for name in self.list_commands(ctx) if name not in seen]
        if remaining:
            rows_by_section.append(
                (
                    "Other Commands",
                    [
                        (
                            name,
                            self.get_command(ctx, name).get_short_help_str(formatter.width),
                        )
                        for name in remaining
                        if self.get_command(ctx, name) is not None
                    ],
                )
            )

        if not rows_by_section:
            return

        with formatter.section("Commands"):
            for section_name, rows in rows_by_section:
                formatter.write_paragraph()
                formatter.write_text(f"{section_name}:")
                formatter.write_dl(rows)


@click.group(
    cls=HippocampusGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--config", "config_path", default=None, help="Config file path.")
@click.option("--output-dir", default=None, help="Output directory.")
@click.option("--verbose", is_flag=True, help="Verbose output.")
@click.option("--quiet", is_flag=True, help="Suppress non-error output.")
@click.pass_context
def cli(ctx, config_path, output_dir, verbose, quiet):
    """Hippocampus — code repository indexing toolkit.

    Quick start:

      First-time setup: hippo onekey
      Incremental refresh: hippo update
      Manual steps: hippo init / sig-extract / tree / index / structure-prompt
      Inspect outputs: hippo overview

    All commands remain available below; the help view is grouped so the
    common workflow appears first.
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path
    ctx.obj["output_dir"] = output_dir
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet


register_core_commands(cli)
snapshot_group = register_snapshot_commands(cli)
register_history_commands(cli)
register_query_commands(cli)
register_viz_command(cli)
