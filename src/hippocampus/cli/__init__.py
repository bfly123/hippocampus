"""Click CLI entry point — hippo command group."""

from __future__ import annotations

from pathlib import Path

import click
from click.formatting import HelpFormatter

from .commands_core import register_core_commands
from .query import register_query_commands, register_viz_command
from .snapshot import register_history_commands, register_snapshot_commands


class HippocampusGroup(click.Group):
    """CLI group that renders top-level commands in curated sections."""

    DEFAULT_COMMAND = "_generate"

    COMMAND_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "Core Workflow",
            (
                "refresh",
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

    @staticmethod
    def _looks_like_path(token: str) -> bool:
        if token in {".", ".."}:
            return True
        if token.startswith(("./", "../", "/", "~")):
            return True
        if "/" in token or "\\" in token:
            return True
        return Path(token).exists()

    def resolve_command(
        self,
        ctx: click.Context,
        args: list[str],
    ) -> tuple[str | None, click.Command | None, list[str]]:
        if args:
            token = args[0]
            cmd = self.get_command(ctx, token)
            if cmd is not None:
                return token, cmd, args[1:]
            if not token.startswith("-") and self._looks_like_path(token):
                default_cmd = self.get_command(ctx, self.DEFAULT_COMMAND)
                if default_cmd is not None:
                    return self.DEFAULT_COMMAND, default_cmd, args
        return super().resolve_command(ctx, args)

    def format_commands(self, ctx: click.Context, formatter: HelpFormatter) -> None:
        rows_by_section: list[tuple[str, list[tuple[str, str]]]] = []
        seen: set[str] = set()

        for section_name, command_names in self.COMMAND_SECTIONS:
            rows: list[tuple[str, str]] = []
            for name in command_names:
                cmd = self.get_command(ctx, name)
                if cmd is None or getattr(cmd, "hidden", False):
                    continue
                seen.add(name)
                rows.append((name, cmd.get_short_help_str(formatter.width)))
            if rows:
                rows_by_section.append((section_name, rows))

        remaining = []
        for name in self.list_commands(ctx):
            if name in seen:
                continue
            cmd = self.get_command(ctx, name)
            if cmd is None or getattr(cmd, "hidden", False):
                continue
            remaining.append(name)
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
    subcommand_metavar="[PATH]|COMMAND [ARGS]...",
)
@click.option("--config", "config_path", default=None, help="Config file path.")
@click.option("--output-dir", default=None, help="Output directory.")
@click.option("--verbose", is_flag=True, help="Verbose output.")
@click.option("--quiet", is_flag=True, help="Suppress non-error output.")
@click.pass_context
def cli(ctx, config_path, output_dir, verbose, quiet):
    """Hippocampus — code repository indexing toolkit.

    Quick start:

    \b
      Full generation: hippo .
      Another repo: hippo /path/to/repo
      Incremental refresh: hippo update
      Force full refresh: hippo refresh .
      Manual steps: hippo init / sig-extract / tree / index / structure-prompt
      Inspect outputs: hippo overview

    Standard outputs:

    \b
      .hippocampus/hippocampus-index.json
      .hippocampus/code-signatures.json
      .hippocampus/tree.json
      .hippocampus/structure-prompt.md
      .hippocampus/hippocampus-viz.html

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
