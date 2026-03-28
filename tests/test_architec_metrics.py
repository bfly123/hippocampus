from __future__ import annotations

from pathlib import Path

import click
from click.testing import CliRunner

from hippocampus.cli.pipeline_command_builders import build_generate_command, build_run_command
from hippocampus.integration.architec_metrics import (
    ArchitecMetricsUnavailable,
    generate_architec_metrics_artifact,
)


def test_generate_architec_metrics_artifact_success(tmp_path, monkeypatch):
    script = tmp_path / "collect_repo_metrics.py"
    rubric = tmp_path / "rubric.json"
    script.write_text("print('ok')\n", encoding="utf-8")
    rubric.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(
        "hippocampus.integration.architec_metrics._resolve_architec_tooling",
        lambda root: (script, rubric),
    )

    def fake_run(cmd, cwd, check, capture_output, text):
        out_path = Path(cmd[cmd.index("--out") + 1])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text('{"scores":{"overall":9.1}}\n', encoding="utf-8")

        class Result:
            returncode = 0
            stdout = "Wrote metrics"
            stderr = ""

        return Result()

    monkeypatch.setattr("hippocampus.integration.architec_metrics.subprocess.run", fake_run)

    status = generate_architec_metrics_artifact(tmp_path)

    assert status.generated is True
    assert status.skipped_reason is None
    assert status.output_path.exists()


def test_generate_architec_metrics_artifact_skips_when_architec_missing(tmp_path, monkeypatch):
    def fail(_root):
        raise ArchitecMetricsUnavailable("architec 未安装，跳过 architect-metrics.json 生成。")

    monkeypatch.setattr(
        "hippocampus.integration.architec_metrics._resolve_architec_tooling",
        fail,
    )

    status = generate_architec_metrics_artifact(tmp_path)

    assert status.generated is False
    assert status.skipped_reason is not None
    assert status.output_path.name == "architect-metrics.json"


def test_generate_command_no_longer_generates_architec_metrics_artifact(tmp_path, monkeypatch):
    @click.command("init")
    @click.argument("target", required=False, default=".")
    def fake_init(target):
        return None

    @click.command("sig-extract")
    @click.argument("target", required=False, default=".")
    def fake_sig_extract(target):
        return None

    @click.command("tree")
    @click.argument("target", required=False, default=".")
    def fake_tree(target):
        return None

    @click.command("tree-diff")
    @click.argument("target", required=False, default=".")
    def fake_tree_diff(target):
        return None

    @click.command("trim")
    @click.argument("target", required=False, default=".")
    def fake_trim(target):
        return None

    @click.command("index")
    @click.argument("target", required=False, default=".")
    def fake_index(target):
        return None

    @click.command("structure-prompt")
    @click.option("--profile")
    @click.argument("target", required=False, default=".")
    def fake_prompt_single(target, profile):
        return None

    @click.command("structure-prompt-all")
    @click.option("--set-default")
    @click.argument("target", required=False, default=".")
    def fake_prompt(target, set_default):
        assert target == str(tmp_path)
        assert set_default == "keep"

    def fake_snapshot(out, message=None):
        return {"snapshot_id": "snap-1"}

    def fake_viz(out, verbose=False):
        path = out / "hippocampus-viz.html"
        path.write_text("<html></html>\n", encoding="utf-8")
        return path

    monkeypatch.setattr("hippocampus.tools.snapshot.save_snapshot", fake_snapshot)
    monkeypatch.setattr("hippocampus.viz.generator.generate_viz_html", fake_viz)
    monkeypatch.setattr(
        "hippocampus.cli.pipeline_command_builders._require_index_llm",
        lambda cfg: None,
    )

    run_cmd = build_run_command(
        command_refs={
            "init": fake_init,
            "sig-extract": fake_sig_extract,
            "tree": fake_tree,
            "tree-diff": fake_tree_diff,
            "structure-prompt": fake_prompt_single,
        },
        trim_cmd=fake_trim,
        index_cmd=fake_index,
    )

    cmd = build_generate_command(
        command_refs={"structure-prompt-all": fake_prompt},
        run_cmd=run_cmd,
    )
    runner = CliRunner()
    result = runner.invoke(
        cmd,
        [str(tmp_path)],
        obj={
            "quiet": False,
            "verbose": False,
            "config_path": None,
            "output_dir": None,
        },
    )

    assert result.exit_code == 0, result.output
    assert "Architec Metrics" not in result.output
