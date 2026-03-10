"""Click CLI entry point — hippo command group."""

from __future__ import annotations

import click

from .cli_architect import register_architect_commands
from .cli_commands_core import register_core_commands
from .cli_hooks import register_hooks_commands
from .cli_query import register_query_commands, register_viz_command
from .cli_snapshot import register_history_commands, register_snapshot_commands


@click.group()
@click.option("--config", "config_path", default=None, help="Config file path.")
@click.option("--output-dir", default=None, help="Output directory.")
@click.option("--verbose", is_flag=True, help="Verbose output.")
@click.option("--quiet", is_flag=True, help="Suppress non-error output.")
@click.pass_context
def cli(ctx, config_path, output_dir, verbose, quiet):
    """Hippocampus — code repository indexing toolkit."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path
    ctx.obj["output_dir"] = output_dir
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet


register_core_commands(cli)
architect_group = register_architect_commands(cli)
hooks_group = register_hooks_commands(cli)
snapshot_group = register_snapshot_commands(cli)
register_history_commands(cli)
register_query_commands(cli)
register_viz_command(cli)
