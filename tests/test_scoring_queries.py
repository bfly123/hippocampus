"""Tests for scoring, overview, and expand queries."""

from __future__ import annotations

from hippocampus.query.expand import build_expand
from hippocampus.query.overview import build_overview
from hippocampus.scoring import compute_module_scores

from scoring_query_fixtures import sample_index, scored_index


class TestComputeModuleScores:
    def test_adds_score_and_tier(self, sample_index):
        compute_module_scores(sample_index)
        for module in sample_index["modules"]:
            assert "core_score" in module
            assert "tier" in module
            assert "role" in module
            assert module["tier"] in ("core", "secondary", "peripheral")
            assert module["role"] in ("core", "infra", "interface", "test", "docs")

    def test_scores_are_bounded(self, sample_index):
        compute_module_scores(sample_index)
        for module in sample_index["modules"]:
            assert 0.0 <= module["core_score"] <= 1.0

    def test_core_module_ranks_highest(self, sample_index):
        compute_module_scores(sample_index)
        modules = {module["id"]: module for module in sample_index["modules"]}
        assert modules["mod-core"]["core_score"] > modules["mod-test"]["core_score"]

    def test_empty_index(self):
        index = {"modules": [], "files": {}}
        compute_module_scores(index)
        assert index["modules"] == []

    def test_returns_index(self, sample_index):
        assert compute_module_scores(sample_index) is sample_index


class TestBuildOverview:
    def test_returns_required_keys(self, scored_index):
        result = build_overview(scored_index, budget=4000)
        assert "content" in result
        assert "consumed_tokens" in result
        assert "layers_included" in result

    def test_l0_always_included(self, scored_index):
        result = build_overview(scored_index, budget=4000)
        assert "L0" in result["layers_included"]
        assert "Project Overview" in result["content"]

    def test_l1_modules_included(self, scored_index):
        result = build_overview(scored_index, budget=4000)
        assert "L1" in result["layers_included"]
        assert "mod-core" in result["content"]

    def test_tiny_budget_only_l0(self, scored_index):
        result = build_overview(scored_index, budget=30)
        assert "L0" in result["layers_included"]

    def test_consumed_within_budget(self, scored_index):
        budget = 4000
        result = build_overview(scored_index, budget=budget)
        assert result["consumed_tokens"] <= budget

    def test_content_is_markdown(self, scored_index):
        assert build_overview(scored_index, budget=4000)["content"].startswith("# ")


class TestBuildExpandModule:
    def test_expand_module_l2(self, scored_index):
        result = build_expand(scored_index, "mod:mod-core", level="L2")
        assert result["path"] == "mod-core"
        assert result["level"] == "L2"
        assert "src/main.py" in result["content"]
        assert "src/engine.py" in result["content"]

    def test_expand_module_l3(self, scored_index):
        result = build_expand(scored_index, "mod:mod-core", level="L3")
        assert "Engine" in result["content"]
        assert "process" in result["content"]

    def test_expand_nonexistent_module(self, scored_index):
        assert "No files found" in build_expand(scored_index, "mod:nonexistent")["content"]


class TestBuildExpandPath:
    def test_expand_path_prefix(self, scored_index):
        result = build_expand(scored_index, "src/api/", level="L2")
        assert "routes.py" in result["content"]
        assert "middleware.py" in result["content"]
        assert "engine.py" not in result["content"]

    def test_expand_single_file(self, scored_index):
        assert "main" in build_expand(scored_index, "src/main.py", level="L3")["content"]

    def test_expand_no_match(self, scored_index):
        assert "No files found" in build_expand(scored_index, "nonexistent/path")["content"]


class TestBuildExpandBudget:
    def test_l3_fallback_to_l2_on_tiny_budget(self, scored_index):
        result = build_expand(scored_index, "mod:mod-core", level="L3", budget=5)
        assert "truncated" in result["content"] or result["level"] == "L2"

    def test_consumed_within_budget(self, scored_index):
        budget = 2000
        result = build_expand(scored_index, "mod:mod-core", level="L2", budget=budget)
        assert result["consumed_tokens"] <= budget
