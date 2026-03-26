"""CLI integration tests — hippo commands against ~/yunwei/claude_codex."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import click
from click.testing import CliRunner

from hippocampus.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestCliHelp:
    def test_main_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Hippocampus" in result.output
        assert "Quick start:" in result.output
        assert "Full generation: hippo ." in result.output
        assert "Another repo: hippo /path/to/repo" in result.output
        assert "Incremental refresh: hippo update" in result.output
        assert "Force full refresh: hippo refresh ." in result.output
        assert "Manual" in result.output
        assert "steps:" in result.output
        assert "hippo init / sig-extract / tree / index / structure-prompt" in result.output
        assert "Inspect" in result.output
        assert "outputs:" in result.output
        assert "hippo overview" in result.output
        assert ".hippocampus/architect-metrics.json" in result.output
        assert "Core Workflow:" in result.output
        assert "Explore & Inspect:" in result.output
        assert "Advanced Tools:" in result.output
        assert "\nonekey" not in result.output

    def test_path_invokes_hidden_generate_flow(self, runner, tmp_path, monkeypatch):
        command = cli.commands["_generate"]
        original_callback = command.callback

        @click.pass_context
        def fake_callback(ctx, target, target_option, prompt_profile, snapshot_message, open_viz):
            del ctx, prompt_profile, snapshot_message, open_viz
            click.echo(f"default target={target_option or target}")

        monkeypatch.setattr(command, "callback", fake_callback)
        try:
            result = runner.invoke(cli, [str(tmp_path)])
        finally:
            monkeypatch.setattr(command, "callback", original_callback)

        assert result.exit_code == 0
        assert f"default target={tmp_path}" in result.output

    def test_update_help(self, runner):
        result = runner.invoke(cli, ["update", "--help"])
        assert result.exit_code == 0
        assert "architec-ready artifacts" in result.output
        assert "--default-prompt" in result.output
        assert "--snapshot-message" in result.output
        assert "--full" in result.output
        assert "--target" not in result.output
        assert "--no-llm" not in result.output

    def test_refresh_help(self, runner):
        result = runner.invoke(cli, ["refresh", "--help"])
        assert result.exit_code == 0
        assert "Force a full refresh" in result.output
        assert "--default-prompt" in result.output
        assert "--snapshot-message" in result.output
        assert "--target" not in result.output

    def test_init_help(self, runner):
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "--target" not in result.output

    def test_sig_extract_help(self, runner):
        result = runner.invoke(cli, ["sig-extract", "--help"])
        assert result.exit_code == 0

    def test_tree_help(self, runner):
        result = runner.invoke(cli, ["tree", "--help"])
        assert result.exit_code == 0

    def test_trim_help(self, runner):
        result = runner.invoke(cli, ["trim", "--help"])
        assert result.exit_code == 0
        assert "--budget" in result.output

    def test_index_help_does_not_expose_no_llm(self, runner):
        result = runner.invoke(cli, ["index", "--help"])
        assert result.exit_code == 0
        assert "--no-llm" not in result.output

    def test_run_help_does_not_expose_no_llm(self, runner):
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "--no-llm" not in result.output

    def test_hooks_command_removed(self, runner):
        result = runner.invoke(cli, ["hooks", "--help"])
        assert result.exit_code != 0
        assert "No such command 'hooks'" in result.output

    def test_memory_command_removed(self, runner):
        result = runner.invoke(cli, ["memory", "--help"])
        assert result.exit_code != 0
        assert "No such command 'memory'" in result.output

    def test_snapshot_help(self, runner):
        result = runner.invoke(cli, ["snapshot", "--help"])
        assert result.exit_code == 0
        assert "save" in result.output

    def test_stats_help(self, runner):
        result = runner.invoke(cli, ["stats", "--help"])
        assert result.exit_code == 0
        assert "--history" in result.output

    def test_overview_help(self, runner):
        result = runner.invoke(cli, ["overview", "--help"])
        assert result.exit_code == 0
        assert "--budget" in result.output

    def test_search_help(self, runner):
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "--pattern" in result.output


class TestCliInit:
    def test_init_creates_hippo_dir(self, runner, tmp_path):
        result = runner.invoke(cli, ["init", str(tmp_path)])
        assert result.exit_code == 0
        hippo_dir = tmp_path / ".hippocampus"
        assert hippo_dir.is_dir()
        assert (hippo_dir / "config.yaml").exists()

    def test_init_idempotent(self, runner, tmp_path):
        runner.invoke(cli, ["init", str(tmp_path)])
        result = runner.invoke(cli, ["init", str(tmp_path)])
        assert result.exit_code == 0
        assert "already exists" in result.output


class TestCliSigExtract:
    """System test: run hippo sig-extract against real codebase."""

    def test_sig_extract_on_target(self, runner, target_path):
        """Run sig-extract on claude_codex, verify output."""
        # First init to set up queries
        runner.invoke(cli, ["init", str(target_path)])
        result = runner.invoke(cli, [
            "sig-extract", str(target_path),
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "signatures" in result.output

        # Verify output file
        out_file = target_path / ".hippocampus" / "code-signatures.json"
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert data["version"] == 1
        assert len(data["files"]) > 0


class TestCliTree:
    """System test: run hippo tree against real codebase (requires repomix)."""

    def test_tree_on_target(self, runner, target_path):
        """Run tree on claude_codex, verify output."""
        runner.invoke(cli, ["init", str(target_path)])
        result = runner.invoke(cli, [
            "tree", str(target_path),
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "nodes" in result.output

        out_file = target_path / ".hippocampus" / "tree.json"
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert data["version"] == 1
        assert data["root"]["type"] == "dir"


class TestCliStructurePrompt:
    """Test hippo structure-prompt (depends on tree.json existing)."""

    def test_structure_prompt_after_tree(self, runner, target_path):
        tree_file = target_path / ".hippocampus" / "tree.json"
        if not tree_file.exists():
            pytest.skip("tree.json not found, run tree test first")
        result = runner.invoke(cli, [
            "structure-prompt", str(target_path),
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "chars" in result.output

        out = target_path / ".hippocampus" / "structure-prompt.md"
        assert out.exists()
        md = out.read_text()
        assert md.startswith("# Repository Structure")
