from __future__ import annotations

from pathlib import Path

from hippocampus.llm.prompt_loader import load_prompt_text, render_prompt, resolve_prompt_text


def test_load_packaged_prompt():
    text = load_prompt_text("phase-1-system.md")
    assert "code analysis assistant" in text


def test_project_prompt_override(tmp_path: Path):
    prompt_dir = tmp_path / ".hippocampus" / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "phase-1-system.md").write_text("override prompt", encoding="utf-8")
    text = load_prompt_text("phase-1-system.md", project_root=tmp_path)
    assert text == "override prompt"


def test_render_prompt_template():
    text = render_prompt(
        "phase-2a-user.md",
        file_summaries="a.py: alpha [core]",
    )
    assert "a.py: alpha [core]" in text


def test_env_prompt_override(monkeypatch, tmp_path: Path):
    prompt_dir = tmp_path / "env-prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "phase-1-system.md").write_text("env override", encoding="utf-8")
    monkeypatch.setenv("HIPPOCAMPUS_PROMPTS_DIR", str(prompt_dir))
    text = load_prompt_text("phase-1-system.md")
    assert text == "env override"


def test_legacy_project_prompt_override(tmp_path: Path):
    prompt_dir = tmp_path / "hippocampus" / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "phase-1-system.md").write_text("legacy override", encoding="utf-8")
    text = load_prompt_text("phase-1-system.md", project_root=tmp_path)
    assert text == "legacy override"


def test_resolve_prompt_text_reference(tmp_path: Path):
    prompt_dir = tmp_path / ".hippocampus" / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "architect-system.md").write_text("prompt body", encoding="utf-8")
    text = resolve_prompt_text("prompt:architect-system.md", project_root=tmp_path)
    assert text == "prompt body"
