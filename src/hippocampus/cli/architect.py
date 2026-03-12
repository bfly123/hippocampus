from __future__ import annotations

import click

from .architect_commands import (
    register_architect_audit_command,
    register_architect_plan_command,
    register_architect_review_command,
)


def register_architect_commands(cli) -> click.Group:
    @cli.group("architect")
    @click.pass_context
    def architect_group(ctx):
        """Architecture analysis tools (audit / review / plan)."""
        pass

    register_architect_audit_command(architect_group)
    register_architect_review_command(architect_group)
    register_architect_plan_command(architect_group)
    return architect_group
