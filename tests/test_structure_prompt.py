"""Tests for hippocampus.tools.structure_prompt — Markdown summary generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hippocampus.tools.structure_prompt import (
    ROLE_CONFIG,
    ROLE_DOCS,
    ROLE_SOURCE,
    ROLE_TEST,
    _sanitize_navigation_brief,
    _validate_navigation_brief_json,
    _render_node,
    _truncate_tree,
    classify_file_role,
    run_structure_prompt,
)
from hippocampus.types import TreeNode
from hippocampus.utils import estimate_tokens, write_json
from hippocampus.constants import TREE_FILE, INDEX_FILE, TREE_DIFF_FILE


class TestRenderNode:
    def test_single_file(self):
        node = TreeNode(id="file:a.py", type="file", name="a.py")
        result = _render_node(node)
        assert "a.py" in result
        assert "/" not in result  # file, no trailing slash

    def test_dir_has_slash(self):
        node = TreeNode(id="dir:src", type="dir", name="src")
        result = _render_node(node)
        assert "src/" in result

    def test_nested_indentation(self):
        root = TreeNode(
            id="dir:.", type="dir", name=".",
            children=[
                TreeNode(id="dir:src", type="dir", name="src", children=[
                    TreeNode(id="file:src/a.py", type="file", name="a.py"),
                ]),
            ],
        )
        result = _render_node(root)
        lines = result.strip().splitlines()
        assert lines[0].strip() == "./"
        assert lines[1].strip() == "src/"
        assert lines[2].strip() == "a.py"

    def test_skip_noise_dirs(self):
        root = TreeNode(
            id="dir:.", type="dir", name=".",
            children=[
                TreeNode(id="dir:.ccb", type="dir", name=".ccb", children=[
                    TreeNode(id="dir:history", type="dir", name="history", children=[
                        TreeNode(id="file:history/a.md", type="file", name="a.md"),
                    ]),
                ]),
                TreeNode(id="dir:src", type="dir", name="src", children=[
                    TreeNode(id="file:src/main.py", type="file", name="main.py"),
                ]),
            ],
        )
        result = _render_node(root)
        assert ".ccb/" not in result
        assert "history/" not in result
        assert "src/" in result
        assert "main.py" in result


class TestTruncateTree:
    def test_small_tree_not_truncated(self):
        root = TreeNode(
            id="dir:.", type="dir", name=".",
            children=[
                TreeNode(id="file:a.py", type="file", name="a.py"),
            ],
        )
        result = _truncate_tree(root, max_chars=10000)
        assert "a.py" in result

    def test_large_tree_truncated(self):
        children = []
        for i in range(200):
            children.append(TreeNode(
                id=f"file:file_{i}.py", type="file", name=f"file_{i}.py",
            ))
        root = TreeNode(id="dir:.", type="dir", name=".", children=[
            TreeNode(id="dir:big", type="dir", name="big", children=children),
        ])
        result = _truncate_tree(root, max_chars=100)
        # Truncated form should mention file/subdir counts
        assert "files" in result or "big" in result


def _sample_index():
    """Minimal hippocampus-index.json data for testing."""
    return {
        "version": 2,
        "project": {
            "overview": "A code indexing system.",
            "architecture": "Pipeline: CLI -> tools -> LLM -> query API",
            "scale": {"files": 10, "modules": 3, "primary_lang": "python"},
        },
        "modules": [
            {
                "id": "mod:core",
                "desc": "Core indexing engine.",
                "file_count": 3,
                "core_score": 0.9,
                "tier": "core",
            },
            {
                "id": "mod:utils",
                "desc": "Utility helpers.",
                "file_count": 2,
                "core_score": 0.3,
                "tier": "secondary",
            },
            {
                "id": "mod:test-suite",
                "desc": "Test suite.",
                "file_count": 2,
                "core_score": 0.4,
                "tier": "core",
            },
        ],
        "files": {
            "src/main.py": {
                "id": "file:src/main.py",
                "type": "file",
                "name": "main.py",
                "lang": "python",
                "desc": "Application entry point.",
                "module": "mod:core",
                "tags": ["lib"],
                "signatures": [{"name": "main", "kind": "function", "line": 1}],
            },
            "src/utils.py": {
                "id": "file:src/utils.py",
                "type": "file",
                "name": "utils.py",
                "lang": "python",
                "desc": "Helper utilities.",
                "module": "mod:utils",
                "tags": ["lib"],
                "signatures": [],
            },
            "tests/test_main.py": {
                "id": "file:tests/test_main.py",
                "type": "file",
                "name": "test_main.py",
                "lang": "python",
                "desc": "Tests for main module.",
                "module": "mod:test-suite",
                "tags": ["test"],
                "signatures": [
                    {"name": "test_run", "kind": "function", "line": 1},
                    {"name": "test_exit", "kind": "function", "line": 10},
                ],
            },
            "tests/test_utils.py": {
                "id": "file:tests/test_utils.py",
                "type": "file",
                "name": "test_utils.py",
                "lang": "python",
                "desc": "Tests for utils.",
                "module": "mod:test-suite",
                "tags": ["test"],
                "signatures": [
                    {"name": "test_helper", "kind": "function", "line": 1},
                ],
            },
        },
    }


def _sample_diff():
    """Minimal tree-diff.json data for testing."""
    return {
        "version": 1,
        "changes": [
            {"id": "file:src/new.py", "type": "file", "name": "new.py", "change": "added"},
            {"id": "file:src/main.py", "type": "file", "name": "main.py", "change": "modified"},
        ],
    }


class TestRunStructurePrompt:
    def test_fallback_tree_only(self, tmp_output, sample_tree_doc):
        """Without index, falls back to tree-only output."""
        write_json(tmp_output / TREE_FILE, sample_tree_doc)

        md = run_structure_prompt(tmp_output)
        assert md.startswith("# Repository Structure")
        assert "```" in md
        assert "src" in md
        # Should NOT have module sections (no index)
        assert "## Modules" not in md

    def test_enriched_with_index(self, tmp_output, sample_tree_doc):
        """With index present, source files in Key Files, test files in Test Files."""
        write_json(tmp_output / TREE_FILE, sample_tree_doc)
        write_json(tmp_output / INDEX_FILE, _sample_index())

        md = run_structure_prompt(tmp_output)
        assert md.startswith("# Repository Structure")
        # L0: project overview
        assert "A code indexing system." in md
        assert "**Architecture**:" in md
        assert "**Scale**:" in md
        # Project map (new)
        assert "## Project Map" in md
        assert "### Entry Points" in md
        # L1: modules
        assert "## Modules" in md
        assert "**core**" in md
        assert "**utils**" in md
        # Tree
        assert "## Directory Tree" in md
        assert "```" in md
        # L2: source files in Key Files
        assert "## Key Files" in md
        assert "src/main.py" in md
        # Test files in separate subsection
        assert "### Test Files" in md
        assert "tests/test_main.py" in md
        # L3: signatures should only contain source files
        if "## Signatures" in md:
            sig_section = md.split("## Signatures")[1]
            assert "test_main.py" not in sig_section
            assert "test_utils.py" not in sig_section

    def test_changes_section(self, tmp_output, sample_tree_doc):
        """With tree-diff.json present, output includes Recent Changes."""
        write_json(tmp_output / TREE_FILE, sample_tree_doc)
        write_json(tmp_output / INDEX_FILE, _sample_index())
        write_json(tmp_output / TREE_DIFF_FILE, _sample_diff())

        md = run_structure_prompt(tmp_output)
        assert "## Recent Changes" in md
        assert "[added]" in md
        assert "[modified]" in md
        assert "new.py" in md

    def test_token_budget_enforcement(self, tmp_output, sample_tree_doc):
        """Output stays within the token budget."""
        write_json(tmp_output / TREE_FILE, sample_tree_doc)
        write_json(tmp_output / INDEX_FILE, _sample_index())
        write_json(tmp_output / TREE_DIFF_FILE, _sample_diff())

        budget = 10000
        md = run_structure_prompt(tmp_output, max_tokens=budget)
        assert estimate_tokens(md) <= budget

    def test_tight_budget_drops_layers(self, tmp_output, sample_tree_doc):
        """With a very tight budget, later layers are dropped."""
        write_json(tmp_output / TREE_FILE, sample_tree_doc)
        write_json(tmp_output / INDEX_FILE, _sample_index())
        write_json(tmp_output / TREE_DIFF_FILE, _sample_diff())

        # Very small budget — should include L0 but may drop later layers
        md = run_structure_prompt(tmp_output, max_tokens=80)
        assert "# Repository Structure" in md
        # Changes section should be dropped with tight budget
        assert "## Recent Changes" not in md

    def test_missing_tree_raises(self, tmp_output):
        with pytest.raises(FileNotFoundError):
            run_structure_prompt(tmp_output)


class TestClassifyFileRole:
    """Tests for classify_file_role — path override > tags > default."""

    def test_path_override_tests_dir(self):
        """Path in tests/ directory → ROLE_TEST even without test tag."""
        assert classify_file_role("tests/foo.py", {}) == ROLE_TEST

    def test_path_override_test_prefix(self):
        """Filename test_foo.py → ROLE_TEST."""
        assert classify_file_role("test_foo.py", {}) == ROLE_TEST

    def test_path_override_conftest(self):
        """conftest.py → ROLE_TEST."""
        assert classify_file_role("conftest.py", {}) == ROLE_TEST

    def test_path_override_config(self):
        """pyproject.toml → ROLE_CONFIG."""
        assert classify_file_role("pyproject.toml", {}) == ROLE_CONFIG

    def test_path_override_yml(self):
        """.yml extension → ROLE_CONFIG."""
        assert classify_file_role(".github/ci.yml", {}) == ROLE_CONFIG

    def test_path_doc(self):
        """README.md → ROLE_DOCS."""
        assert classify_file_role("README.md", {}) == ROLE_DOCS

    def test_tag_test(self):
        """Tag 'test' → ROLE_TEST (when path doesn't match)."""
        assert classify_file_role("src/helpers.py", {"tags": ["test"]}) == ROLE_TEST

    def test_tag_config(self):
        """Tag 'config' → ROLE_CONFIG."""
        assert classify_file_role("src/settings.py", {"tags": ["config"]}) == ROLE_CONFIG

    def test_tag_lib_is_source(self):
        """Tag 'lib' (no special meaning) → ROLE_SOURCE."""
        assert classify_file_role("src/core.py", {"tags": ["lib"]}) == ROLE_SOURCE

    def test_no_match_is_source(self):
        """No tag, no path match → ROLE_SOURCE."""
        assert classify_file_role("src/engine.py", {}) == ROLE_SOURCE


class TestNavigationBriefValidation:
    def test_validate_navigation_brief_json_ok(self):
        known = {"src/main.py", "src/utils.py", "src/"}
        text = json.dumps({
            "summary": "repo summary",
            "reading_order": [
                {"path": "src/main.py", "why": "entrypoint"},
            ],
            "architecture_axes": ["pipeline"],
            "risk_hotspots": [
                {"path": "src/utils.py", "risk": "medium", "reason": "shared utility"},
            ],
        })
        assert _validate_navigation_brief_json(text, known) == []

    def test_validate_navigation_brief_json_rejects_unknown_path(self):
        known = {"src/main.py"}
        text = json.dumps({
            "summary": "repo summary",
            "reading_order": [{"path": "evil/path.py", "why": "nope"}],
            "architecture_axes": ["pipeline"],
            "risk_hotspots": [],
        })
        errors = _validate_navigation_brief_json(text, known)
        assert any("path not in repository" in e for e in errors)

    def test_sanitize_navigation_brief_filters_invalid_and_dedups(self):
        known = {"src/main.py", "src/utils.py"}
        data = {
            "summary": "x",
            "reading_order": [
                {"path": "src/main.py", "why": "entry"},
                {"path": "src/main.py", "why": "dup"},
                {"path": "unknown.py", "why": "bad"},
            ],
            "architecture_axes": ["a", "", "b"],
            "risk_hotspots": [
                {"path": "src/utils.py", "risk": "high", "reason": "core"},
                {"path": "unknown.py", "risk": "low", "reason": "bad"},
            ],
        }
        cleaned = _sanitize_navigation_brief(data, known)
        assert cleaned["reading_order"] == [{"path": "src/main.py", "why": "entry"}]
        assert cleaned["architecture_axes"] == ["a", "b"]
        assert cleaned["risk_hotspots"] == [
            {"path": "src/utils.py", "risk": "high", "reason": "core"}
        ]
