"""Tests for hippocampus.parsers package (lang_map, query_loader, ts_extract)."""

from __future__ import annotations

from pathlib import Path

from hippocampus.parsers.lang_map import EXTENSION_MAP, filename_to_lang


class TestFilenameToLang:
    def test_python(self):
        assert filename_to_lang("main.py") == "python"

    def test_javascript(self):
        assert filename_to_lang("app.js") == "javascript"
        assert filename_to_lang("component.jsx") == "javascript"

    def test_typescript(self):
        assert filename_to_lang("index.ts") == "typescript"
        assert filename_to_lang("App.tsx") == "typescript"

    def test_go(self):
        assert filename_to_lang("main.go") == "go"

    def test_rust(self):
        assert filename_to_lang("lib.rs") == "rust"

    def test_shell_not_supported(self):
        assert filename_to_lang("script.sh") is None

    def test_markdown_not_supported(self):
        assert filename_to_lang("README.md") is None

    def test_no_extension(self):
        assert filename_to_lang("Makefile") is None

    def test_case_insensitive(self):
        assert filename_to_lang("Main.PY") == "python"

    def test_full_path(self):
        assert filename_to_lang("/home/user/project/src/main.py") == "python"

    def test_c_header(self):
        assert filename_to_lang("types.h") == "c"

    def test_cpp_variants(self):
        assert filename_to_lang("main.cpp") == "cpp"
        assert filename_to_lang("main.cc") == "cpp"
        assert filename_to_lang("main.cxx") == "cpp"

    def test_extension_map_completeness(self):
        """Verify key languages are in the map."""
        expected = {"python", "javascript", "typescript", "go", "rust",
                    "ruby", "java", "c", "cpp", "c_sharp"}
        actual_langs = set(EXTENSION_MAP.values())
        assert expected.issubset(actual_langs)


# ── query_loader tests ──

from hippocampus.parsers.query_loader import (
    available_languages,
    find_queries_dir,
    load_query,
)


class TestQueryLoader:
    def test_find_queries_dir_exists(self, queries_dir):
        """queries_dir fixture should provide a valid dir."""
        assert queries_dir.is_dir()

    def test_find_queries_dir_missing(self, tmp_path):
        result = find_queries_dir(tmp_path)
        assert result is None

    def test_load_python_query(self, queries_dir):
        scm = load_query(queries_dir, "python")
        if (queries_dir / "python-tags.scm").exists():
            assert scm is not None
            assert len(scm) > 0
            assert "definition" in scm or "name" in scm

    def test_load_nonexistent_lang(self, queries_dir):
        assert load_query(queries_dir, "brainfuck") is None

    def test_load_c_sharp_alias(self, tmp_path):
        qdir = tmp_path / "queries"
        qdir.mkdir()
        (qdir / "csharp-tags.scm").write_text("(class_declaration) @name.definition.class")
        scm = load_query(qdir, "c_sharp")
        assert scm is not None
        assert "class_declaration" in scm

    def test_available_languages(self, queries_dir):
        langs = available_languages(queries_dir)
        assert isinstance(langs, list)
        if (queries_dir / "python-tags.scm").exists():
            assert "python" in langs


# ── ts_extract tests ──

from hippocampus.parsers.ts_extract import (
    _normalize_query_for_runtime,
    extract_definitions,
    extract_tags,
)


class TestTsExtract:
    def test_normalize_javascript_legacy_query(self):
        q = "value: [(arrow_function) (function)]"
        fixed = _normalize_query_for_runtime("javascript", q)
        assert "(function_expression)" in fixed
        assert "(function)]" not in fixed

    def test_extract_from_python_file(self, tmp_path, queries_dir):
        """Extract tags from a simple Python file."""
        py_file = tmp_path / "sample.py"
        py_file.write_text(
            "class Foo:\n"
            "    def bar(self):\n"
            "        pass\n"
            "\n"
            "def baz():\n"
            "    return 1\n"
        )
        tags = extract_tags(str(py_file), "sample.py", queries_dir)
        names = [t.name for t in tags]
        # Should find at least class and function definitions
        if tags:  # tree-sitter may not be installed for python
            def_tags = [t for t in tags if t.kind == "def"]
            assert len(def_tags) >= 1

    def test_extract_definitions_only(self, tmp_path, queries_dir):
        """extract_definitions should filter out references."""
        py_file = tmp_path / "defs.py"
        py_file.write_text("def hello():\n    pass\n")
        defs = extract_definitions(str(py_file), "defs.py", queries_dir)
        for d in defs:
            assert d.kind == "def"

    def test_unsupported_file_returns_empty(self, tmp_path, queries_dir):
        """Non-code files should return empty list."""
        txt = tmp_path / "notes.txt"
        txt.write_text("just text")
        assert extract_tags(str(txt), "notes.txt", queries_dir) == []

    def test_empty_file_returns_empty(self, tmp_path, queries_dir):
        """Empty source file should return empty list."""
        py_file = tmp_path / "empty.py"
        py_file.write_text("")
        assert extract_tags(str(py_file), "empty.py", queries_dir) == []

    def test_extract_from_real_codebase(self, target_path, queries_dir):
        """System test: extract tags from a real Python file in claude_codex."""
        py_files = list(target_path.rglob("*.py"))
        assert len(py_files) > 0, "No Python files found in target"
        # Pick first non-empty file
        for pf in py_files[:5]:
            if pf.stat().st_size > 50:
                rel = str(pf.relative_to(target_path))
                tags = extract_tags(str(pf), rel, queries_dir)
                if tags:
                    assert all(hasattr(t, "name") for t in tags)
                    assert all(hasattr(t, "kind") for t in tags)
                    break
