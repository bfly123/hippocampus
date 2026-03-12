"""Shared test fixtures for hippocampus system tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hippocampus.resources import copy_packaged_queries

# Target codebase for system tests
TARGET_CODEBASE = Path.home() / "yunwei" / "claude_codex"


@pytest.fixture
def target_path():
    """Path to the real target codebase."""
    assert TARGET_CODEBASE.is_dir(), f"Target codebase not found: {TARGET_CODEBASE}"
    return TARGET_CODEBASE


@pytest.fixture
def tmp_output(tmp_path):
    """Temporary output directory for test artifacts."""
    out = tmp_path / ".hippocampus"
    out.mkdir()
    return out


@pytest.fixture
def tmp_project(tmp_path):
    """Temporary project directory with minimal structure."""
    proj = tmp_path / "project"
    proj.mkdir()
    return proj


@pytest.fixture
def queries_dir(tmp_output):
    """Copy packaged .scm query files into tmp output for tests."""
    dst = tmp_output / "queries"
    copy_packaged_queries(dst)
    return dst


@pytest.fixture
def sample_tree_doc():
    """A minimal tree document dict for testing."""
    return {
        "version": 1,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "root": {
            "id": "dir:.",
            "type": "dir",
            "name": ".",
            "children": [
                {
                    "id": "dir:src",
                    "type": "dir",
                    "name": "src",
                    "children": [
                        {"id": "file:src/main.py", "type": "file", "name": "main.py", "children": []},
                        {"id": "file:src/utils.py", "type": "file", "name": "utils.py", "children": []},
                    ],
                },
                {
                    "id": "dir:tests",
                    "type": "dir",
                    "name": "tests",
                    "children": [
                        {"id": "file:tests/test_main.py", "type": "file", "name": "test_main.py", "children": []},
                    ],
                },
                {"id": "file:README.md", "type": "file", "name": "README.md", "children": []},
            ],
        },
    }


@pytest.fixture
def sample_compress_data():
    """Minimal repomix compress-style data for testing."""
    return {
        "files": {
            "src/main.py": "def main():\n    print('hello')\n",
            "src/utils.py": "def helper():\n    return 42\n",
            "lib/core.py": "class Core:\n    pass\n" * 20,
            "lib/extra.py": "x = 1\n",
            "README.md": "# Project\n",
        }
    }
