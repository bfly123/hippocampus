from __future__ import annotations

from hippocampus.cli import cli


def test_architect_group_and_subcommands_registered():
    assert "architect" in cli.commands
    architect_group = cli.commands["architect"]
    assert "audit" in architect_group.commands
    assert "review" in architect_group.commands
    assert "plan" in architect_group.commands


def test_architect_subcommands_callbacks_come_from_split_module():
    architect_group = cli.commands["architect"]
    expected_module = "hippocampus.cli.architect_commands"
    assert architect_group.commands["audit"].callback.__module__ == expected_module
    assert architect_group.commands["review"].callback.__module__ == expected_module
    assert architect_group.commands["plan"].callback.__module__ == expected_module
