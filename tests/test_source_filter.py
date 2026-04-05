from __future__ import annotations

from pathlib import Path

from hippocampus.source_filter import (
    build_file_manifest,
    classify_project_file,
    should_include_architecture_file,
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


def test_classify_project_file_detects_extensionless_code_and_skips_non_code(tmp_path: Path) -> None:
    script = tmp_path / "ccb"
    license_file = tmp_path / "LICENSE"
    blob = tmp_path / "payload"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "from cli.entrypoint import run_cli_entrypoint\n"
        "\n"
        "def main():\n"
        "    return run_cli_entrypoint()\n",
        encoding="utf-8",
    )
    license_file.write_text("GNU Affero General Public License\n", encoding="utf-8")
    blob.write_bytes(b"\x00\x01\x02")

    source = classify_project_file("ccb", project_root=tmp_path)
    doc = classify_project_file("LICENSE", project_root=tmp_path)
    binary = classify_project_file("payload", project_root=tmp_path)

    assert source.kind == "source"
    assert source.language == "python"
    assert source.include_in_architecture is True
    assert doc.kind == "doc"
    assert binary.kind == "ignored"
    assert binary.include_in_architecture is False


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


def test_build_file_manifest_includes_extensionless_code_but_skips_doc_and_binary(tmp_path: Path) -> None:
    (tmp_path / "ccb").write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "\n"
        "def main():\n"
        "    return sys.argv[0]\n",
        encoding="utf-8",
    )
    (tmp_path / "LICENSE").write_text("GNU Affero General Public License\n", encoding="utf-8")
    (tmp_path / "payload").write_bytes(b"\x00\x01\x02")

    manifest = build_file_manifest(tmp_path)
    files = manifest["files"]

    assert "ccb" in files
    assert files["ccb"]["kind"] == "source"
    assert files["ccb"]["language"] == "python"
    assert "LICENSE" not in files
    assert "payload" not in files


def test_should_include_tree_path_excludes_tests_docs_and_build() -> None:
    assert should_include_tree_path(Path("src/core")) is True
    assert should_include_tree_path(Path("src/core/app.py")) is True
    assert should_include_tree_path(Path("tests/test_app.py")) is False
    assert should_include_tree_path(Path("docs/architecture.md")) is False
    assert should_include_tree_path(Path("dist/bundle.js")) is False


def test_build_file_manifest_applies_shared_and_hippo_rules(tmp_path: Path) -> None:
    (tmp_path / "src" / "keep").mkdir(parents=True)
    (tmp_path / "src" / "legacy").mkdir(parents=True)
    (tmp_path / "tmp").mkdir(parents=True)
    (tmp_path / "src" / "keep" / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (tmp_path / "src" / "legacy" / "old.py").write_text("def old():\n    return 1\n", encoding="utf-8")
    (tmp_path / "tmp" / "skip.py").write_text("def skip():\n    return 1\n", encoding="utf-8")
    (tmp_path / "skip_me.py").write_text("def skip_me():\n    return 1\n", encoding="utf-8")
    (tmp_path / ".architecture-rules.toml").write_text(
        "\n".join(
            [
                "[shared]",
                'ignore_paths = ["tmp"]',
                "",
                "[hippo]",
                'ignore_paths = ["src/legacy"]',
                'ignore_globs = ["skip_*.py"]',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = build_file_manifest(tmp_path)
    files = manifest["files"]

    assert "src/keep/app.py" in files
    assert "src/legacy/old.py" not in files
    assert "tmp/skip.py" not in files
    assert "skip_me.py" not in files


def test_should_include_architecture_file_applies_hippo_rule_file(tmp_path: Path) -> None:
    (tmp_path / ".architecture-rules.toml").write_text(
        "\n".join(
            [
                "[hippo]",
                'ignore_extensions = [".gen"]',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    from hippocampus.architecture_rules import load_hippo_rules

    rules = load_hippo_rules(tmp_path)

    assert should_include_architecture_file("src/app.py", rules=rules) is True
    assert should_include_architecture_file("src/schema.gen", rules=rules) is False
    assert should_include_tree_path(Path("src/schema.gen"), rules=rules) is False
