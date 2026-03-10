"""Tests for index diff — module matching, stats, files, and integration."""

from __future__ import annotations

import pytest

from hippocampus.query.diff import (
    _diff_files,
    _diff_modules,
    _diff_stats,
    _match_modules,
    build_diff,
)


@pytest.fixture
def old_index():
    """Baseline index for diff testing."""
    return {
        "version": 2,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "project": {"overview": "Old project"},
        "modules": [
            {"id": "mod-core", "desc": "Core engine", "file_count": 2},
            {"id": "mod-api", "desc": "API layer", "file_count": 1},
        ],
        "files": {
            "src/main.py": {
                "module": "mod-core",
                "tags": ["python", "entrypoint"],
                "signatures": [{"name": "main", "kind": "function", "line": 1}],
            },
            "src/engine.py": {
                "module": "mod-core",
                "tags": ["python", "core"],
                "signatures": [
                    {"name": "Engine", "kind": "class", "line": 1},
                    {"name": "run", "kind": "method", "line": 5},
                ],
            },
            "src/api.py": {
                "module": "mod-api",
                "tags": ["python", "api"],
                "signatures": [{"name": "handler", "kind": "function", "line": 1}],
            },
        },
        "stats": {
            "total_files": 3,
            "total_modules": 2,
            "total_signatures": 4,
        },
    }


@pytest.fixture
def new_index():
    """Changed index: added file, removed file, moved module, changed tags."""
    return {
        "version": 2,
        "generated_at": "2026-01-02T00:00:00+00:00",
        "project": {"overview": "New project"},
        "modules": [
            {"id": "core-engine", "desc": "Core engine v2", "file_count": 2},
            {"id": "mod-web", "desc": "Web layer", "file_count": 1},
        ],
        "files": {
            "src/main.py": {
                "module": "core-engine",
                "tags": ["python", "entrypoint", "cli"],
                "signatures": [{"name": "main", "kind": "function", "line": 1}],
            },
            "src/engine.py": {
                "module": "core-engine",
                "tags": ["python", "core"],
                "signatures": [
                    {"name": "Engine", "kind": "class", "line": 1},
                    {"name": "run", "kind": "method", "line": 5},
                    {"name": "stop", "kind": "method", "line": 15},
                ],
            },
            "src/web.py": {
                "module": "mod-web",
                "tags": ["python", "web"],
                "signatures": [{"name": "serve", "kind": "function", "line": 1}],
            },
        },
        "stats": {
            "total_files": 3,
            "total_modules": 2,
            "total_signatures": 5,
        },
    }


class TestMatchModules:
    def test_jaccard_match(self, old_index, new_index):
        result = _match_modules(
            old_index["modules"], old_index["files"],
            new_index["modules"], new_index["files"],
        )
        # mod-core shares main.py + engine.py with core-engine
        assert len(result["matched"]) == 1
        om, nm, j = result["matched"][0]
        assert om["id"] == "mod-core"
        assert nm["id"] == "core-engine"
        assert j >= 0.3

    def test_no_match_below_threshold(self):
        old_mods = [{"id": "a", "desc": "A"}]
        old_files = {"x.py": {"module": "a"}}
        new_mods = [{"id": "b", "desc": "B"}]
        new_files = {"y.py": {"module": "b"}}
        result = _match_modules(old_mods, old_files, new_mods, new_files)
        assert len(result["matched"]) == 0
        assert len(result["removed"]) == 1
        assert len(result["added"]) == 1

    def test_empty_modules(self):
        result = _match_modules([], {}, [], {})
        assert result == {"matched": [], "added": [], "removed": []}


class TestDiffStats:
    def test_positive_delta(self, old_index, new_index):
        result = _diff_stats(old_index, new_index)
        assert result["files"] == 0
        assert result["modules"] == 0
        assert result["signatures"] == 1

    def test_no_change(self, old_index):
        result = _diff_stats(old_index, old_index)
        assert result == {"files": 0, "modules": 0, "signatures": 0}


class TestDiffModules:
    def test_added_and_removed(self, old_index, new_index):
        match = _match_modules(
            old_index["modules"], old_index["files"],
            new_index["modules"], new_index["files"],
        )
        result = _diff_modules(old_index, new_index, match)
        # mod-api removed (no file overlap with mod-web)
        removed_ids = [m["id"] for m in result["modules_removed"]]
        assert "mod-api" in removed_ids
        # mod-web added
        added_ids = [m["id"] for m in result["modules_added"]]
        assert "mod-web" in added_ids

    def test_changed_modules(self, old_index, new_index):
        match = _match_modules(
            old_index["modules"], old_index["files"],
            new_index["modules"], new_index["files"],
        )
        result = _diff_modules(old_index, new_index, match)
        assert len(result["modules_changed"]) == 1
        mc = result["modules_changed"][0]
        assert mc["old_id"] == "mod-core"
        assert mc["new_id"] == "core-engine"


class TestDiffFiles:
    def test_added_and_removed(self, old_index, new_index):
        result = _diff_files(old_index, new_index)
        assert "src/web.py" in result["files_added"]
        assert "src/api.py" in result["files_removed"]

    def test_tag_changes(self, old_index, new_index):
        result = _diff_files(old_index, new_index)
        tag_paths = [f["path"] for f in result["files_tag_changed"]]
        assert "src/main.py" in tag_paths
        tc = next(f for f in result["files_tag_changed"] if f["path"] == "src/main.py")
        assert "cli" in tc["added"]

    def test_no_changes(self, old_index):
        result = _diff_files(old_index, old_index)
        assert result["files_added"] == []
        assert result["files_removed"] == []
        assert result["files_moved"] == []
        assert result["files_tag_changed"] == []


class TestBuildDiff:
    def test_return_format(self, old_index, new_index):
        result = build_diff(old_index, new_index, old_id="v1", new_id="v2")
        assert result["old_id"] == "v1"
        assert result["new_id"] == "v2"
        assert "stats_diff" in result
        assert "modules_added" in result
        assert "modules_removed" in result
        assert "modules_changed" in result
        assert "files_added" in result
        assert "files_removed" in result
        assert "content" in result
        assert "consumed_tokens" in result

    def test_change_magnitude(self, old_index, new_index):
        result = build_diff(old_index, new_index)
        assert result["change_magnitude"] > 0

    def test_markdown_content(self, old_index, new_index):
        result = build_diff(old_index, new_index)
        assert "# Index Diff" in result["content"]
        assert "Stats Changes" in result["content"]


class TestBuildDiffEdgeCases:
    def test_same_index(self, old_index):
        result = build_diff(old_index, old_index)
        assert result["change_magnitude"] == 0
        assert result["stats_diff"] == {"files": 0, "modules": 0, "signatures": 0}

    def test_empty_index(self):
        empty = {"modules": [], "files": {}, "stats": {}}
        result = build_diff(empty, empty)
        assert result["change_magnitude"] == 0

    def test_module_rename_no_false_moves(self):
        """When module ID changes but files stay, no moves should be reported."""
        old = {
            "modules": [{"id": "mod-a", "desc": "A"}],
            "files": {
                "x.py": {"module": "mod-a", "tags": ["py"], "signatures": []},
                "y.py": {"module": "mod-a", "tags": ["py"], "signatures": []},
            },
            "stats": {"total_files": 2, "total_modules": 1, "total_signatures": 0},
        }
        new = {
            "modules": [{"id": "renamed-a", "desc": "A v2"}],
            "files": {
                "x.py": {"module": "renamed-a", "tags": ["py"], "signatures": []},
                "y.py": {"module": "renamed-a", "tags": ["py"], "signatures": []},
            },
            "stats": {"total_files": 2, "total_modules": 1, "total_signatures": 0},
        }
        result = build_diff(old, new)
        assert result["files_moved"] == []
        assert len(result["modules_changed"]) == 1
