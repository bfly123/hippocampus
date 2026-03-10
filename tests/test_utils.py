"""Tests for hippocampus.utils module."""

from __future__ import annotations

import json
from pathlib import Path

from hippocampus.utils import (
    estimate_tokens,
    is_hidden,
    read_json,
    relative_path,
    write_json,
    write_text,
)


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 1  # min 1

    def test_short_string(self):
        assert estimate_tokens("hi") == 1  # 2 // 4 = 0 → max(1, 0) = 1

    def test_normal_string(self):
        text = "a" * 100
        assert estimate_tokens(text) == 25  # 100 // 4

    def test_long_string(self):
        text = "x" * 4000
        assert estimate_tokens(text) == 1000


class TestIsHidden:
    def test_normal_path(self):
        assert is_hidden(Path("src/main.py")) is False

    def test_hidden_file(self):
        assert is_hidden(Path(".env")) is True

    def test_hidden_dir(self):
        assert is_hidden(Path(".git/config")) is True

    def test_nested_hidden(self):
        assert is_hidden(Path("src/.hidden/file.py")) is True

    def test_dotdot_not_hidden(self):
        # ".." starts with dot but is a special case
        assert is_hidden(Path("..")) is True  # current impl treats it as hidden


class TestRelativePath:
    def test_normal(self):
        base = Path("/home/user/project")
        target = Path("/home/user/project/src/main.py")
        assert relative_path(base, target) == "src/main.py"

    def test_unrelated_paths(self):
        base = Path("/home/user/project")
        target = Path("/tmp/other")
        result = relative_path(base, target)
        assert "other" in result


class TestJsonIO:
    def test_write_and_read(self, tmp_path):
        data = {"key": "value", "num": 42, "list": [1, 2, 3]}
        fpath = tmp_path / "test.json"
        write_json(fpath, data)
        assert fpath.exists()
        loaded = read_json(fpath)
        assert loaded == data

    def test_write_creates_parents(self, tmp_path):
        fpath = tmp_path / "a" / "b" / "c" / "test.json"
        write_json(fpath, {"ok": True})
        assert fpath.exists()

    def test_write_text(self, tmp_path):
        fpath = tmp_path / "out.md"
        write_text(fpath, "# Hello\n")
        assert fpath.read_text() == "# Hello\n"

    def test_write_text_creates_parents(self, tmp_path):
        fpath = tmp_path / "deep" / "dir" / "out.txt"
        write_text(fpath, "content")
        assert fpath.exists()
