from __future__ import annotations

from .cli_commands_pipeline import register_pipeline_commands
from .cli_commands_project_bootstrap import register_project_bootstrap_commands
from .cli_commands_structure_prompt import register_structure_prompt_commands


def register_core_commands(cli) -> None:
    command_refs: dict[str, object] = {}
    command_refs.update(register_project_bootstrap_commands(cli))
    command_refs.update(register_structure_prompt_commands(cli))
    command_refs.update(register_pipeline_commands(cli, command_refs))


__all__ = ["register_core_commands"]
