from __future__ import annotations

from click.testing import CliRunner

from hippocampus.cli import cli


CORE_COMMANDS = {
    "_generate",
    "refresh",
    "update",
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
    "_generate": "hippocampus.cli.pipeline_command_builders",
    "refresh": "hippocampus.cli.pipeline_command_builders",
    "update": "hippocampus.cli.pipeline_command_builders",
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
    init_result = runner.invoke(cli, ["init", str(tmp_path)])
    assert init_result.exit_code == 0
    result = runner.invoke(
        cli,
        ["index", "--no-llm", str(tmp_path)],
    )
    assert result.exit_code == 0


def test_update_runs_incremental_refresh_without_llm(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "demo.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    def fake_metrics(target):
        out = tmp_path / ".hippocampus" / "architect-metrics.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("{}\n", encoding="utf-8")

        class Status:
            skipped_reason = None
            output_path = out

        return Status()

    runner = CliRunner()
    from hippocampus.cli import pipeline_command_builders

    original = pipeline_command_builders.generate_architec_metrics_artifact
    pipeline_command_builders.generate_architec_metrics_artifact = fake_metrics
    try:
        result = runner.invoke(
            cli,
            ["update", "--no-llm", str(tmp_path)],
        )
    finally:
        pipeline_command_builders.generate_architec_metrics_artifact = original
    assert result.exit_code == 0

    out = tmp_path / ".hippocampus"
    assert (out / "architect-metrics.json").exists()
    assert (out / "hippocampus-index.json").exists()
    assert (out / "code-signatures.json").exists()
    assert (out / "tree.json").exists()
    assert (out / "structure-prompt-map.md").exists()
    assert (out / "structure-prompt-deep.md").exists()
    assert (out / "structure-prompt.md").exists()
    assert (out / "hippocampus-viz.html").exists()
    assert (out / "snapshots").is_dir()


def test_refresh_invokes_update_with_full(tmp_path, monkeypatch):
    runner = CliRunner()
    seen: dict[str, object] = {}
    update_cmd = cli.commands["update"]
    original_callback = update_cmd.callback

    def fake_update(target, default_prompt, snapshot_message, open_viz, full, no_llm):
        seen["target"] = target
        seen["default_prompt"] = default_prompt
        seen["snapshot_message"] = snapshot_message
        seen["open_viz"] = open_viz
        seen["full"] = full
        seen["no_llm"] = no_llm

    monkeypatch.setattr(update_cmd, "callback", fake_update)
    try:
        result = runner.invoke(cli, ["refresh", str(tmp_path)])
    finally:
        monkeypatch.setattr(update_cmd, "callback", original_callback)

    assert result.exit_code == 0
    assert seen["target"] == str(tmp_path)
    assert seen["full"] is True
    assert seen["no_llm"] is False
