from __future__ import annotations

from click.testing import CliRunner

from hippocampus.cli import cli


CORE_COMMANDS = {
    "init",
    "sig-extract",
    "tree",
    "tree-diff",
    "structure-prompt",
    "structure-prompt-all",
    "repomap",
    "trim",
    "index",
    "run",
}

EXPECTED_MODULES = {
    "init": "hippocampus.cli.commands_project_bootstrap",
    "sig-extract": "hippocampus.cli.commands_project_bootstrap",
    "tree": "hippocampus.cli.commands_project_bootstrap",
    "tree-diff": "hippocampus.cli.commands_project_bootstrap",
    "structure-prompt": "hippocampus.cli.commands_structure_prompt",
    "structure-prompt-all": "hippocampus.cli.commands_structure_prompt",
    "repomap": "hippocampus.cli.pipeline_command_builders",
    "trim": "hippocampus.cli.pipeline_command_builders",
    "index": "hippocampus.cli.pipeline_command_builders",
    "run": "hippocampus.cli.pipeline_command_builders",
}


def test_core_commands_registered_from_core_module():
    for name in CORE_COMMANDS:
        assert name in cli.commands
        assert cli.commands[name].callback.__module__ == EXPECTED_MODULES[name]


def test_index_accepts_no_llm_option(tmp_path):
    runner = CliRunner()
    init_result = runner.invoke(cli, ["init", "--target", str(tmp_path)])
    assert init_result.exit_code == 0
    result = runner.invoke(
        cli,
        ["index", "--target", str(tmp_path), "--no-llm"],
    )
    assert result.exit_code == 0
