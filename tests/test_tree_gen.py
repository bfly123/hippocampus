"""Tests for hippocampus.tools.tree_gen — directory structure parsing."""

from __future__ import annotations

from pathlib import Path

from hippocampus.tools.tree_gen import (
    _is_dir_entry,
    _parse_indent,
    parse_directory_structure,
)
from hippocampus.types import TreeNode


class TestParseIndent:
    def test_no_indent(self):
        level, name = _parse_indent("src/")
        assert level == 0
        assert name == "src/"

    def test_two_space_indent(self):
        level, name = _parse_indent("  main.py")
        assert level == 1
        assert name == "main.py"

    def test_four_space_indent(self):
        level, name = _parse_indent("    utils.py")
        assert level == 2
        assert name == "utils.py"

    def test_empty_line(self):
        level, name = _parse_indent("")
        assert level == -1

    def test_blank_line(self):
        level, name = _parse_indent("   ")
        assert level == -1 or name == ""


class TestIsDirEntry:
    def test_dir_with_slash(self):
        assert _is_dir_entry("src/") is True

    def test_file_no_slash(self):
        assert _is_dir_entry("main.py") is False

    def test_dotfile(self):
        assert _is_dir_entry(".gitignore") is False


class TestParseDirectoryStructure:
    def test_simple_tree(self):
        text = "src/\n  main.py\n  utils.py\nREADME.md\n"
        root = parse_directory_structure(text)
        assert root.id == "dir:."
        assert root.type == "dir"
        assert len(root.children) == 2  # src/ and README.md

        src = root.children[0]
        assert src.type == "dir"
        assert src.name == "src"
        assert len(src.children) == 2

    def test_nested_dirs(self):
        text = "src/\n  lib/\n    core.py\n  main.py\n"
        root = parse_directory_structure(text)
        src = root.children[0]
        assert src.name == "src"
        lib = src.children[0]
        assert lib.name == "lib"
        assert lib.type == "dir"
        assert len(lib.children) == 1
        assert lib.children[0].name == "core.py"

    def test_empty_text(self):
        root = parse_directory_structure("")
        assert root.id == "dir:."
        assert len(root.children) == 0

    def test_node_ids(self):
        text = "src/\n  main.py\n"
        root = parse_directory_structure(text)
        src = root.children[0]
        assert src.id == "dir:src"
        assert src.children[0].id == "file:src/main.py"

    def test_file_at_root(self):
        text = "setup.py\n"
        root = parse_directory_structure(text)
        assert len(root.children) == 1
        assert root.children[0].type == "file"
        assert root.children[0].name == "setup.py"

    def test_runtime_artifacts_are_filtered(self):
        text = (
            ".hippocampus/\n"
            "  tree.json\n"
            "llm-proxy/\n"
            "  latest-context.json\n"
            "  llm-proxy-viz.html\n"
            "  src/\n"
            "    app.py\n"
            "opencode.json\n"
        )
        root = parse_directory_structure(text)
        names = [child.name for child in root.children]
        assert ".hippocampus" not in names
        assert "opencode.json" not in names
        assert names == ["llm-proxy"]
        llm_proxy = root.children[0]
        assert [child.name for child in llm_proxy.children] == ["src"]
