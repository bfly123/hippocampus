"""Tests for hippo_search query module."""

from __future__ import annotations

import pytest

from hippocampus.query.search import (
    _tag_score,
    _pattern_score,
    _combined_score,
    build_search,
)


@pytest.fixture
def sample_index():
    """A minimal hippocampus index for testing search."""
    return {
        "version": 2,
        "schema": "hippocampus-index/v2",
        "project": {
            "overview": "A sample project for testing.",
            "scale": {"files": 6, "modules": 3, "primary_lang": "python"},
        },
        "modules": [
            {"id": "mod-core", "desc": "Core engine", "file_count": 3},
            {"id": "mod-api", "desc": "API layer", "file_count": 2},
            {"id": "mod-test", "desc": "Test suite", "file_count": 1},
        ],
        "files": {
            "src/main.py": {
                "id": "file:src/main.py",
                "type": "file",
                "name": "main.py",
                "lang": "python",
                "desc": "Application entrypoint",
                "tags": ["entrypoint", "python"],
                "module": "mod-core",
                "signatures": [
                    {"name": "main", "kind": "function", "line": 1, "desc": "Entry"},
                    {"name": "setup", "kind": "function", "line": 10, "desc": "Init"},
                ],
            },
            "src/engine.py": {
                "id": "file:src/engine.py",
                "type": "file",
                "name": "engine.py",
                "lang": "python",
                "desc": "Core processing engine",
                "tags": ["core", "python"],
                "module": "mod-core",
                "signatures": [
                    {"name": "Engine", "kind": "class", "line": 1, "desc": "Main engine"},
                    {"name": "process", "kind": "method", "line": 5, "desc": "Process data"},
                    {"name": "validate", "kind": "method", "line": 20, "desc": "Validate input"},
                ],
            },
            "src/utils.py": {
                "id": "file:src/utils.py",
                "type": "file",
                "name": "utils.py",
                "lang": "python",
                "desc": "Utility helpers",
                "tags": ["util", "python"],
                "module": "mod-core",
                "signatures": [
                    {"name": "helper", "kind": "function", "line": 1, "desc": "A helper"},
                ],
            },
            "src/api/routes.py": {
                "id": "file:src/api/routes.py",
                "type": "file",
                "name": "routes.py",
                "lang": "python",
                "desc": "HTTP route definitions",
                "tags": ["api", "python"],
                "module": "mod-api",
                "signatures": [
                    {"name": "get_users", "kind": "function", "line": 1, "desc": "List users"},
                    {"name": "create_user", "kind": "function", "line": 10, "desc": "Create user"},
                ],
            },
            "src/api/middleware.py": {
                "id": "file:src/api/middleware.py",
                "type": "file",
                "name": "middleware.py",
                "lang": "python",
                "desc": "Request middleware",
                "tags": ["api", "python"],
                "module": "mod-api",
                "signatures": [],
            },
            "tests/test_engine.py": {
                "id": "file:tests/test_engine.py",
                "type": "file",
                "name": "test_engine.py",
                "lang": "python",
                "desc": "Engine unit tests",
                "tags": ["test", "python"],
                "module": "mod-test",
                "signatures": [
                    {"name": "test_process", "kind": "function", "line": 1, "desc": "Test process"},
                ],
            },
        },
    }


# ── Tag score tests ──

class TestTagScore:
    def test_full_match(self):
        assert _tag_score(["python", "core"], ["core", "python"]) == 1.0

    def test_partial_match(self):
        assert _tag_score(["python", "api"], ["python", "core"]) == 0.5

    def test_no_match(self):
        assert _tag_score(["api", "web"], ["core", "python"]) == 0.0

    def test_empty_query_tags(self):
        assert _tag_score([], ["core", "python"]) == 0.0

    def test_empty_file_tags(self):
        assert _tag_score(["python"], []) == 0.0

    def test_single_tag_match(self):
        assert _tag_score(["python"], ["python", "core"]) == 1.0


# ── Pattern score tests ──

class TestPatternScore:
    def test_filepath_match(self):
        fd = {"desc": "unrelated", "signatures": []}
        assert _pattern_score("engine", "src/engine.py", fd) == 1.0

    def test_filepath_case_insensitive(self):
        fd = {"desc": "unrelated", "signatures": []}
        assert _pattern_score("ENGINE", "src/engine.py", fd) == 1.0

    def test_desc_match(self):
        fd = {"desc": "Core processing engine", "signatures": []}
        assert _pattern_score("processing", "src/foo.py", fd) == 0.7

    def test_signature_name_match(self):
        fd = {"desc": "unrelated", "signatures": [{"name": "validate"}]}
        assert _pattern_score("validate", "src/foo.py", fd) == 0.5

    def test_no_match(self):
        fd = {"desc": "unrelated", "signatures": [{"name": "foo"}]}
        assert _pattern_score("zzz", "src/bar.py", fd) == 0.0

    def test_empty_pattern(self):
        fd = {"desc": "anything", "signatures": []}
        assert _pattern_score("", "src/main.py", fd) == 0.0

    def test_filepath_takes_priority_over_desc(self):
        fd = {"desc": "engine stuff", "signatures": [{"name": "engine"}]}
        # filepath match (1.0) should win over desc (0.7) and sig (0.5)
        assert _pattern_score("engine", "src/engine.py", fd) == 1.0


# ── Combined score tests ──

class TestCombinedScore:
    def test_tags_only(self):
        fd = {"tags": ["python", "core"], "desc": "", "signatures": []}
        score = _combined_score(["python"], None, "src/foo.py", fd)
        assert score == 1.0

    def test_pattern_only(self):
        fd = {"tags": ["python"], "desc": "Core engine", "signatures": []}
        score = _combined_score(None, "engine", "src/engine.py", fd)
        assert score == 1.0  # filepath match

    def test_both_combined(self):
        fd = {"tags": ["python", "core"], "desc": "", "signatures": []}
        # tag_score = 1/2 = 0.5 (only "python" matches from ["python", "api"])
        # pattern_score = 1.0 (filepath match)
        score = _combined_score(["python", "api"], "engine", "src/engine.py", fd)
        expected = 0.6 * 0.5 + 0.4 * 1.0  # 0.7
        assert abs(score - expected) < 1e-9

    def test_neither(self):
        fd = {"tags": ["python"], "desc": "", "signatures": []}
        score = _combined_score(None, None, "src/foo.py", fd)
        assert score == 0.0

    def test_empty_tags_list_treated_as_no_tags(self):
        fd = {"tags": ["python"], "desc": "", "signatures": []}
        score = _combined_score([], "engine", "src/engine.py", fd)
        assert score == 1.0  # pattern only

    def test_whitespace_pattern_treated_as_no_pattern(self):
        fd = {"tags": ["python", "core"], "desc": "", "signatures": []}
        score = _combined_score(["python"], "   ", "src/foo.py", fd)
        assert score == 1.0  # tags only


# ── Integration tests ──

class TestBuildSearch:
    def test_returns_required_keys(self, sample_index):
        result = build_search(sample_index, tags=["python"])
        assert "matches" in result
        assert "consumed_tokens" in result
        assert "content" in result

    def test_tag_search_returns_matches(self, sample_index):
        result = build_search(sample_index, tags=["api"])
        paths = [m["path"] for m in result["matches"]]
        assert "src/api/routes.py" in paths
        assert "src/api/middleware.py" in paths

    def test_pattern_search_filepath(self, sample_index):
        result = build_search(sample_index, pattern="engine")
        paths = [m["path"] for m in result["matches"]]
        assert "src/engine.py" in paths
        # test_engine.py also matches on filepath
        assert "tests/test_engine.py" in paths

    def test_results_sorted_by_score_desc(self, sample_index):
        result = build_search(sample_index, tags=["python"])
        scores = [m["score"] for m in result["matches"]]
        assert scores == sorted(scores, reverse=True)

    def test_limit_respected(self, sample_index):
        result = build_search(sample_index, tags=["python"], limit=2)
        assert len(result["matches"]) <= 2

    def test_empty_results(self, sample_index):
        result = build_search(sample_index, tags=["nonexistent"])
        assert result["matches"] == []

    def test_content_is_markdown(self, sample_index):
        result = build_search(sample_index, tags=["python"])
        assert result["content"].startswith("# Search Results")

    def test_consumed_tokens_positive(self, sample_index):
        result = build_search(sample_index, tags=["python"])
        assert result["consumed_tokens"] > 0

    def test_match_has_required_fields(self, sample_index):
        result = build_search(sample_index, tags=["core"])
        assert len(result["matches"]) > 0
        m = result["matches"][0]
        assert "path" in m
        assert "desc" in m
        assert "score" in m
        assert "tags" in m
        assert "module" in m


class TestBuildSearchEdgeCases:
    def test_none_tags_and_pattern(self, sample_index):
        result = build_search(sample_index, tags=None, pattern=None)
        assert result["matches"] == []

    def test_empty_tags_list(self, sample_index):
        result = build_search(sample_index, tags=[], pattern="engine")
        # Should behave as pattern-only
        paths = [m["path"] for m in result["matches"]]
        assert "src/engine.py" in paths

    def test_whitespace_pattern(self, sample_index):
        result = build_search(sample_index, tags=["python"], pattern="   ")
        # Should behave as tags-only
        assert len(result["matches"]) > 0

    def test_combined_search(self, sample_index):
        result = build_search(sample_index, tags=["api"], pattern="route")
        paths = [m["path"] for m in result["matches"]]
        assert "src/api/routes.py" in paths

    def test_all_python_files_match(self, sample_index):
        result = build_search(sample_index, tags=["python"], limit=100)
        # All 6 files have "python" tag
        assert len(result["matches"]) == 6

    def test_empty_index(self):
        idx = {"files": {}}
        result = build_search(idx, tags=["python"])
        assert result["matches"] == []
        assert "No matching" in result["content"]

    def test_markdown_contains_query_info(self, sample_index):
        result = build_search(sample_index, tags=["api"], pattern="route")
        assert "api" in result["content"]
        assert "route" in result["content"]
