from __future__ import annotations

from pathlib import Path

from hippocampus.source_filter import (
    build_file_manifest,
    classify_project_file,
    should_include_tree_path,
)


def test_classify_project_file_distinguishes_source_test_and_generated() -> None:
    source = classify_project_file("src/service/engine.py")
    test = classify_project_file("tests/test_engine.py")
    generated = classify_project_file("src/service/user_pb2.py")
    infra = classify_project_file("terraform/main.tf")

    assert source.kind == "source"
    assert source.include_in_architecture is True
    assert test.kind == "test"
    assert test.include_in_architecture is False
    assert test.include_in_test_support is True
    assert generated.kind == "generated"
    assert infra.kind == "infra"


def test_build_file_manifest_keeps_source_and_test_but_skips_hidden_runtime(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".hippocampus").mkdir()
    (tmp_path / "src" / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (tmp_path / "tests" / "test_app.py").write_text("def test_run():\n    assert True\n", encoding="utf-8")
    (tmp_path / ".venv" / "lib" / "noise.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".hippocampus" / "tree.json").write_text("{}", encoding="utf-8")

    manifest = build_file_manifest(tmp_path)
    files = manifest["files"]

    assert "src/app.py" in files
    assert files["src/app.py"]["kind"] == "source"
    assert "tests/test_app.py" in files
    assert files["tests/test_app.py"]["kind"] == "test"
    assert ".venv/lib/noise.py" not in files
    assert ".hippocampus/tree.json" not in files


def test_should_include_tree_path_excludes_tests_docs_and_build() -> None:
    assert should_include_tree_path(Path("src/core")) is True
    assert should_include_tree_path(Path("src/core/app.py")) is True
    assert should_include_tree_path(Path("tests/test_app.py")) is False
    assert should_include_tree_path(Path("docs/architecture.md")) is False
    assert should_include_tree_path(Path("dist/bundle.js")) is False
