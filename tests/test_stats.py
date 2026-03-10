"""Tests for index stats — distribution, tags, top files, rendering, history."""

from __future__ import annotations

import pytest

from hippocampus.query.stats import (
    _module_distribution,
    _render_bar,
    _render_sparkline,
    _tag_frequency,
    _top_files,
    build_stats,
    build_stats_history,
)


@pytest.fixture
def sample_index():
    """A minimal index for stats testing."""
    return {
        "version": 2,
        "modules": [
            {"id": "mod-core", "desc": "Core", "file_count": 3, "tier": "core"},
            {"id": "mod-api", "desc": "API", "file_count": 2, "tier": "secondary"},
            {"id": "mod-test", "desc": "Tests", "file_count": 1, "tier": "peripheral"},
        ],
        "files": {
            "src/main.py": {
                "module": "mod-core",
                "tags": ["python", "entrypoint"],
                "signatures": [
                    {"name": "main", "kind": "function", "line": 1},
                    {"name": "setup", "kind": "function", "line": 10},
                ],
            },
            "src/engine.py": {
                "module": "mod-core",
                "tags": ["python", "core"],
                "signatures": [
                    {"name": "Engine", "kind": "class", "line": 1},
                    {"name": "run", "kind": "method", "line": 5},
                    {"name": "stop", "kind": "method", "line": 15},
                ],
            },
            "src/utils.py": {
                "module": "mod-core",
                "tags": ["python", "util"],
                "signatures": [
                    {"name": "helper", "kind": "function", "line": 1},
                ],
            },
            "src/api/routes.py": {
                "module": "mod-api",
                "tags": ["python", "api"],
                "signatures": [
                    {"name": "get_users", "kind": "function", "line": 1},
                    {"name": "create_user", "kind": "function", "line": 10},
                ],
            },
            "src/api/middleware.py": {
                "module": "mod-api",
                "tags": ["python", "api"],
                "signatures": [],
            },
            "tests/test_engine.py": {
                "module": "mod-test",
                "tags": ["python", "test"],
                "signatures": [
                    {"name": "test_run", "kind": "function", "line": 1},
                ],
            },
        },
        "stats": {
            "total_files": 6,
            "total_modules": 3,
            "total_signatures": 9,
        },
    }


class TestModuleDistribution:
    def test_correct_counts(self, sample_index):
        result = _module_distribution(sample_index)
        core = next(m for m in result if m["id"] == "mod-core")
        assert core["file_count"] == 3
        assert core["sig_count"] == 6

    def test_sorted_by_file_count(self, sample_index):
        result = _module_distribution(sample_index)
        counts = [m["file_count"] for m in result]
        assert counts == sorted(counts, reverse=True)

    def test_tier_included(self, sample_index):
        result = _module_distribution(sample_index)
        core = next(m for m in result if m["id"] == "mod-core")
        assert core["tier"] == "core"


class TestTagFrequency:
    def test_descending_order(self, sample_index):
        result = _tag_frequency(sample_index)
        counts = [c for _, c in result]
        assert counts == sorted(counts, reverse=True)

    def test_correct_count(self, sample_index):
        result = _tag_frequency(sample_index)
        python_count = next(c for t, c in result if t == "python")
        assert python_count == 6


class TestTopFiles:
    def test_sorted_by_sig_count(self, sample_index):
        result = _top_files(sample_index)
        counts = [f["sig_count"] for f in result]
        assert counts == sorted(counts, reverse=True)

    def test_limit(self, sample_index):
        result = _top_files(sample_index, n=2)
        assert len(result) == 2


class TestRenderBar:
    def test_format(self):
        line = _render_bar("mod-core", 10, 10, width=10)
        assert "█" * 10 in line
        assert "mod-core" in line

    def test_zero_value(self):
        line = _render_bar("empty", 0, 10, width=10)
        assert "░" * 10 in line

    def test_zero_max(self):
        line = _render_bar("zero", 0, 0, width=10)
        assert "░" * 10 in line


class TestRenderSparkline:
    def test_mapping(self):
        result = _render_sparkline([0, 50, 100])
        assert len(result) == 3
        assert result[0] == "▁"
        assert result[-1] == "█"

    def test_constant_values(self):
        result = _render_sparkline([5, 5, 5])
        assert len(result) == 3
        assert len(set(result)) == 1

    def test_empty(self):
        assert _render_sparkline([]) == ""


class TestBuildStats:
    def test_return_format(self, sample_index):
        result = build_stats(sample_index)
        assert "modules" in result
        assert "tier_summary" in result
        assert "top_files" in result
        assert "tag_freq" in result
        assert "consumed_tokens" in result
        assert "content" in result

    def test_markdown_has_bar_chart(self, sample_index):
        result = build_stats(sample_index)
        assert "█" in result["content"]
        assert "Module Distribution" in result["content"]

    def test_tier_summary(self, sample_index):
        result = build_stats(sample_index)
        assert result["tier_summary"]["core"] == 1
        assert result["tier_summary"]["secondary"] == 1
        assert result["tier_summary"]["peripheral"] == 1


class TestBuildStatsHistory:
    def test_multiple_snapshots(self):
        snaps = [
            {
                "generated_at": "2026-01-01",
                "stats": {"total_files": 10, "total_modules": 2, "total_signatures": 20},
            },
            {
                "generated_at": "2026-01-02",
                "stats": {"total_files": 15, "total_modules": 3, "total_signatures": 30},
            },
            {
                "generated_at": "2026-01-03",
                "stats": {"total_files": 20, "total_modules": 3, "total_signatures": 40},
            },
        ]
        result = build_stats_history(snaps)
        assert result["snapshots_count"] == 3
        assert "Trends" in result["content"]
        assert result["consumed_tokens"] > 0

    def test_single_snapshot_fallback(self):
        snaps = [
            {"generated_at": "2026-01-01", "stats": {"total_files": 10}},
        ]
        result = build_stats_history(snaps)
        assert result["snapshots_count"] == 1
        assert result["content"] == ""

    def test_empty_list(self):
        result = build_stats_history([])
        assert result["snapshots_count"] == 0
        assert result["content"] == ""

    def test_missing_stats_keys(self):
        """History should handle snapshots with missing stats gracefully."""
        snaps = [
            {"generated_at": "2026-01-01", "stats": {}},
            {"generated_at": "2026-01-02", "stats": {"total_files": 5}},
        ]
        result = build_stats_history(snaps)
        assert result["snapshots_count"] == 2
        assert "Trends" in result["content"]
