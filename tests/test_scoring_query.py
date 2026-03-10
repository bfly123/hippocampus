"""Tests for scoring, query/overview, and query/expand modules."""

from __future__ import annotations

import pytest

from hippocampus.scoring import (
    _file_role_bonus,
    _classify_tier,
    _classify_file_viz_role,
    _classify_module_role,
    compute_module_scores,
)
from hippocampus.query.overview import build_overview
from hippocampus.query.expand import build_expand


@pytest.fixture
def sample_index():
    """A minimal hippocampus index for testing scoring and query APIs."""
    return {
        "version": 2,
        "schema": "hippocampus-index/v2",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "project": {
            "overview": "A sample project for testing.",
            "architecture": "Monolithic Python app.",
            "scale": {
                "files": 6,
                "modules": 3,
                "primary_lang": "python",
            },
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
                    {"name": "process", "kind": "method", "line": 5, "parent": "Engine", "desc": "Process data"},
                    {"name": "validate", "kind": "method", "line": 20, "parent": "Engine", "desc": "Validate input"},
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
        "stats": {
            "total_files": 6,
            "total_modules": 3,
            "total_signatures": 9,
        },
    }


# ── Scoring tests ──

class TestFileRoleBonus:
    def test_entrypoint_tag(self):
        assert _file_role_bonus(["entrypoint", "python"]) == 1.0

    def test_api_tag(self):
        assert _file_role_bonus(["api", "python"]) == 0.8

    def test_test_tag(self):
        assert _file_role_bonus(["test", "python"]) == 0.2

    def test_no_match(self):
        assert _file_role_bonus(["python", "data"]) == 0.0

    def test_first_match_wins(self):
        # "entrypoint" matches before "test"
        assert _file_role_bonus(["entrypoint", "test"]) == 1.0


class TestClassifyTier:
    def test_core(self):
        assert _classify_tier(0.35) == "core"
        assert _classify_tier(0.30) == "core"

    def test_secondary(self):
        assert _classify_tier(0.15) == "secondary"
        assert _classify_tier(0.10) == "secondary"

    def test_peripheral(self):
        assert _classify_tier(0.05) == "peripheral"
        assert _classify_tier(0.0) == "peripheral"


class TestClassifyFileVizRole:
    """Per-file role classification: path-first + tag fallback."""

    # ── Path-based rules ──

    def test_tests_dir(self):
        assert _classify_file_viz_role("tests/test_engine.py", {}) == "test"

    def test_test_prefix(self):
        assert _classify_file_viz_role("test_foo.py", {}) == "test"

    def test_test_suffix(self):
        assert _classify_file_viz_role("engine_test.py", {}) == "test"

    def test_spec_suffix(self):
        assert _classify_file_viz_role("engine_spec.py", {}) == "test"

    def test_conftest(self):
        assert _classify_file_viz_role("tests/conftest.py", {}) == "test"

    def test_markdown_docs(self):
        assert _classify_file_viz_role("README.md", {}) == "docs"

    def test_docs_dir(self):
        assert _classify_file_viz_role("docs/guide.txt", {}) == "docs"

    def test_license(self):
        assert _classify_file_viz_role("LICENSE", {}) == "docs"

    def test_changelog(self):
        assert _classify_file_viz_role("CHANGELOG.md", {}) == "docs"

    def test_yaml_infra(self):
        assert _classify_file_viz_role("config.yml", {}) == "infra"

    def test_toml_infra(self):
        assert _classify_file_viz_role("pyproject.toml", {}) == "infra"

    def test_setup_py_infra(self):
        assert _classify_file_viz_role("setup.py", {}) == "infra"

    def test_makefile_infra(self):
        assert _classify_file_viz_role("Makefile", {}) == "infra"

    def test_dockerfile_infra(self):
        assert _classify_file_viz_role("Dockerfile", {}) == "infra"

    def test_dotenv_infra(self):
        assert _classify_file_viz_role(".env", {}) == "infra"

    def test_cli_dir_interface(self):
        assert _classify_file_viz_role("cli/main.py", {}) == "interface"

    def test_mcp_dir_interface(self):
        assert _classify_file_viz_role("mcp/server.py", {}) == "interface"

    def test_web_dir_interface(self):
        assert _classify_file_viz_role("web/app.py", {}) == "interface"

    # ── Tag fallback ──

    def test_tag_test(self):
        assert _classify_file_viz_role("src/foo.py", {"tags": ["test"]}) == "test"

    def test_tag_entrypoint_interface(self):
        assert _classify_file_viz_role("src/foo.py", {"tags": ["entrypoint"]}) == "interface"

    def test_tag_config_infra(self):
        assert _classify_file_viz_role("src/foo.py", {"tags": ["config"]}) == "infra"

    def test_tag_util_infra(self):
        assert _classify_file_viz_role("src/foo.py", {"tags": ["util"]}) == "infra"

    def test_tag_docs(self):
        assert _classify_file_viz_role("src/foo.py", {"tags": ["docs"]}) == "docs"

    def test_no_match_defaults_core(self):
        assert _classify_file_viz_role("src/engine.py", {"tags": ["python"]}) == "core"

    # ── Path takes priority over tags ──

    def test_path_overrides_tag(self):
        # Path says test, tags say config — path wins
        assert _classify_file_viz_role("tests/test_config.py", {"tags": ["config"]}) == "test"


class TestClassifyModuleRole:
    """Module role via per-file majority vote (path-driven, no overrides)."""

    def test_test_files_vote_test(self):
        files = [
            ("tests/test_foo.py", {"tags": ["test", "python"]}),
            ("tests/test_bar.py", {"tags": ["test", "python"]}),
        ]
        assert _classify_module_role("mod:some-tests", files) == "test"

    def test_core_files_vote_core(self):
        files = [
            ("src/engine.py", {"tags": ["lib", "python"]}),
            ("src/parser.py", {"tags": ["core", "python"]}),
        ]
        assert _classify_module_role("mod:engine", files) == "core"

    def test_infra_files_vote_infra(self):
        files = [
            ("setup.py", {"tags": ["config", "python"]}),
            ("config.yml", {"tags": ["util", "python"]}),
        ]
        assert _classify_module_role("mod:utils", files) == "infra"

    def test_md_files_vote_docs(self):
        files = [
            ("README.md", {"tags": []}),
            ("docs/GUIDE.md", {"tags": []}),
        ]
        assert _classify_module_role("mod:documentation", files) == "docs"

    def test_empty_files_default_core(self):
        assert _classify_module_role("mod:empty", []) == "core"

    def test_tiebreak_core_wins(self):
        # One core file, one infra file → core wins tiebreak
        files = [
            ("src/lib.py", {"tags": ["lib", "python"]}),
            ("setup.cfg", {"tags": ["config", "python"]}),
        ]
        assert _classify_module_role("mod:mixed", files) == "core"

    def test_path_driven_ignores_module_id(self):
        # Even with a "testing"-like module ID, classification is path-driven
        files = [
            ("src/engine.py", {"tags": ["core"]}),
            ("src/parser.py", {"tags": ["lib"]}),
        ]
        assert _classify_module_role("mod:testing", files) == "core"


class TestComputeModuleScores:
    def test_adds_score_and_tier(self, sample_index):
        compute_module_scores(sample_index)
        for mod in sample_index["modules"]:
            assert "core_score" in mod
            assert "tier" in mod
            assert "role" in mod
            assert mod["tier"] in ("core", "secondary", "peripheral")
            assert mod["role"] in ("core", "infra", "interface", "test", "docs")

    def test_scores_are_bounded(self, sample_index):
        compute_module_scores(sample_index)
        for mod in sample_index["modules"]:
            assert 0.0 <= mod["core_score"] <= 1.0

    def test_core_module_ranks_highest(self, sample_index):
        compute_module_scores(sample_index)
        mods = {m["id"]: m for m in sample_index["modules"]}
        # mod-core has 3 files, 6 sigs, entrypoint+core+util tags
        # mod-test has 1 file, 1 sig, test tag
        assert mods["mod-core"]["core_score"] > mods["mod-test"]["core_score"]

    def test_empty_index(self):
        idx = {"modules": [], "files": {}}
        compute_module_scores(idx)
        assert idx["modules"] == []

    def test_returns_index(self, sample_index):
        result = compute_module_scores(sample_index)
        assert result is sample_index


# ── Overview tests ──

@pytest.fixture
def scored_index(sample_index):
    """Sample index with core_score computed."""
    compute_module_scores(sample_index)
    return sample_index


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
        # Very small budget should only fit L0
        result = build_overview(scored_index, budget=30)
        assert "L0" in result["layers_included"]
        # L1 may or may not fit depending on L0 size

    def test_consumed_within_budget(self, scored_index):
        budget = 4000
        result = build_overview(scored_index, budget=budget)
        assert result["consumed_tokens"] <= budget

    def test_content_is_markdown(self, scored_index):
        result = build_overview(scored_index, budget=4000)
        assert result["content"].startswith("# ")


# ── Expand tests ──

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
        result = build_expand(scored_index, "mod:nonexistent")
        assert "No files found" in result["content"]


class TestBuildExpandPath:
    def test_expand_path_prefix(self, scored_index):
        result = build_expand(scored_index, "src/api/", level="L2")
        assert "routes.py" in result["content"]
        assert "middleware.py" in result["content"]
        # Should NOT include files outside prefix
        assert "engine.py" not in result["content"]

    def test_expand_single_file(self, scored_index):
        result = build_expand(scored_index, "src/main.py", level="L3")
        assert "main" in result["content"]

    def test_expand_no_match(self, scored_index):
        result = build_expand(scored_index, "nonexistent/path")
        assert "No files found" in result["content"]


class TestBuildExpandBudget:
    def test_l3_fallback_to_l2_on_tiny_budget(self, scored_index):
        # Very small budget should cause L3 to fall back to L2 or truncate
        result = build_expand(scored_index, "mod:mod-core", level="L3", budget=5)
        # Should either fall back to L2 or truncate
        assert "truncated" in result["content"] or result["level"] == "L2"

    def test_consumed_within_budget(self, scored_index):
        budget = 2000
        result = build_expand(scored_index, "mod:mod-core", level="L2", budget=budget)
        assert result["consumed_tokens"] <= budget
