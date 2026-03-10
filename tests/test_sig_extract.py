"""Tests for hippocampus.tools.sig_extract — system tests against real codebase."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from hippocampus.tools.sig_extract import (
    _collect_source_files,
    _infer_parent,
    run_sig_extract,
)
from hippocampus.types import CodeSignaturesDoc


class TestCollectSourceFiles:
    def test_finds_python_files(self, target_path):
        files = _collect_source_files(target_path)
        py_files = [f for f in files if f.suffix == ".py"]
        assert len(py_files) > 0

    def test_skips_hidden_dirs(self, target_path):
        files = _collect_source_files(target_path)
        for f in files:
            rel = f.relative_to(target_path)
            parts = rel.parts
            assert not any(p.startswith(".") for p in parts)

    def test_only_supported_languages(self, target_path):
        from hippocampus.parsers.lang_map import filename_to_lang
        files = _collect_source_files(target_path)
        for f in files:
            assert filename_to_lang(str(f)) is not None


class TestInferParent:
    def test_method_gets_parent_class(self):
        from hippocampus.parsers.ts_extract import Tag
        tags = [
            Tag(rel_fname="f.py", fname="f.py", name="MyClass",
                kind="def", line=0, tag_type="class"),
            Tag(rel_fname="f.py", fname="f.py", name="my_method",
                kind="def", line=5, tag_type="function"),
        ]
        parent = _infer_parent(tags, tags[1])
        assert parent == "MyClass"

    def test_no_parent_for_top_level(self):
        from hippocampus.parsers.ts_extract import Tag
        tags = [
            Tag(rel_fname="f.py", fname="f.py", name="standalone",
                kind="def", line=0, tag_type="function"),
        ]
        parent = _infer_parent(tags, tags[0])
        assert parent is None


class TestRunSigExtract:
    """System test: run full sig_extract against ~/yunwei/claude_codex."""

    def test_run_against_real_codebase(self, target_path, tmp_output, queries_dir):
        """Run sig_extract on claude_codex and validate output schema."""
        # Ensure queries are in the expected location
        hippo_dir = target_path / ".hippocampus"
        needs_cleanup = False
        if not hippo_dir.exists():
            hippo_dir.mkdir()
            needs_cleanup = True
        q_dst = hippo_dir / "queries"
        if not q_dst.exists():
            shutil.copytree(queries_dir, q_dst)

        try:
            doc = run_sig_extract(target_path, tmp_output, verbose=False)
        finally:
            if needs_cleanup:
                shutil.rmtree(hippo_dir, ignore_errors=True)

        # Validate return type
        assert isinstance(doc, CodeSignaturesDoc)
        assert doc.version == 1
        assert len(doc.generated_at) > 0

        # Should find Python files
        assert len(doc.files) > 0
        py_files = {k: v for k, v in doc.files.items() if v.lang == "python"}
        assert len(py_files) > 0, "Should find Python signatures"

        # Validate signature structure
        for fpath, fsig in doc.files.items():
            assert isinstance(fsig.lang, str)
            assert len(fsig.signatures) > 0
            for sig in fsig.signatures:
                assert isinstance(sig.name, str) and len(sig.name) > 0
                assert sig.kind in ("class", "function", "method", "const",
                                     "module", "interface", "type", "")
                assert isinstance(sig.line, int) and sig.line >= 0

    def test_output_file_written(self, target_path, tmp_output, queries_dir):
        """Verify JSON output file is created."""
        hippo_dir = target_path / ".hippocampus"
        needs_cleanup = False
        if not hippo_dir.exists():
            hippo_dir.mkdir()
            needs_cleanup = True
        q_dst = hippo_dir / "queries"
        if not q_dst.exists():
            shutil.copytree(queries_dir, q_dst)

        try:
            run_sig_extract(target_path, tmp_output, verbose=False)
        finally:
            if needs_cleanup:
                shutil.rmtree(hippo_dir, ignore_errors=True)

        from hippocampus.constants import CODE_SIGNATURES_FILE
        out_file = tmp_output / CODE_SIGNATURES_FILE
        assert out_file.exists()

        import json
        data = json.loads(out_file.read_text())
        assert data["version"] == 1
        assert "files" in data
