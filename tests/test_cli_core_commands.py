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
    "init": "hippocampus.cli_commands_project_bootstrap",
    "sig-extract": "hippocampus.cli_commands_project_bootstrap",
    "tree": "hippocampus.cli_commands_project_bootstrap",
    "tree-diff": "hippocampus.cli_commands_project_bootstrap",
    "structure-prompt": "hippocampus.cli_commands_structure_prompt",
    "structure-prompt-all": "hippocampus.cli_commands_structure_prompt",
    "repomap": "hippocampus.cli_pipeline_command_builders",
    "trim": "hippocampus.cli_pipeline_command_builders",
    "index": "hippocampus.cli_pipeline_command_builders",
    "run": "hippocampus.cli_pipeline_command_builders",
}


def test_core_commands_registered_from_core_module():
    for name in CORE_COMMANDS:
        assert name in cli.commands
        assert cli.commands[name].callback.__module__ == EXPECTED_MODULES[name]


def test_index_rejects_no_llm_with_phase(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["index", "--target", str(tmp_path), "--no-llm", "--phase", "1"],
    )
    assert result.exit_code == 2
    assert "--no-llm cannot be combined with --phase" in result.output
