"""Tests for RepoMap snippet extraction."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from hippocampus.tools.repomap_adapter import HippoRepoMap, check_repomap_available


@pytest.fixture
def temp_repo():
    """Create a temporary repository with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create test files
        (root / "test.py").write_text("""
class TestClass:
    def method_one(self):
        pass

    def method_two(self):
        pass

def standalone_function():
    return 42
""")

        (root / "utils.py").write_text("""
def helper_function():
    return "helper"

class UtilClass:
    pass
""")

        yield root


def test_get_ranked_snippets_basic(temp_repo):
    """Test basic snippet extraction."""
    # Skip if RepoMap not available
    available, _ = check_repomap_available(temp_repo)
    if not available:
        pytest.skip("RepoMap not available")

    repomap = HippoRepoMap(temp_repo, verbose=False)

    # Mock ranked tags
    ranked_tags = [
        ("test.py", str(temp_repo / "test.py"), 2, "TestClass", "class"),
        ("test.py", str(temp_repo / "test.py"), 3, "method_one", "def"),
        ("utils.py", str(temp_repo / "utils.py"), 2, "helper_function", "def"),
    ]

    ranked_files = [
        ("test.py", 0.9),
        ("utils.py", 0.5),
    ]

    snippets = repomap.get_ranked_snippets(
        ranked_tags=ranked_tags,
        ranked_files=ranked_files,
        max_snippets_per_file=2,
        global_token_budget=2500,
        per_snippet_token_cap=500,
    )

    assert len(snippets) > 0
    assert snippets[0]["file"] == "test.py"
    assert "snippets" in snippets[0]
    assert "total_tokens" in snippets[0]


def test_snippet_budget_control(temp_repo):
    """Test global token budget enforcement."""
    available, _ = check_repomap_available(temp_repo)
    if not available:
        pytest.skip("RepoMap not available")

    repomap = HippoRepoMap(temp_repo, verbose=False)

    ranked_tags = [
        ("test.py", str(temp_repo / "test.py"), 2, "TestClass", "class"),
    ]

    ranked_files = [("test.py", 0.9)]

    # Very small budget
    snippets = repomap.get_ranked_snippets(
        ranked_tags=ranked_tags,
        ranked_files=ranked_files,
        global_token_budget=10,  # Very small
    )

    # Should respect budget
    total_tokens = sum(s["total_tokens"] for s in snippets)
    assert total_tokens <= 10


def test_snippet_per_file_cap(temp_repo):
    """Test max snippets per file limit."""
    available, _ = check_repomap_available(temp_repo)
    if not available:
        pytest.skip("RepoMap not available")

    repomap = HippoRepoMap(temp_repo, verbose=False)

    ranked_tags = [
        ("test.py", str(temp_repo / "test.py"), 2, "TestClass", "class"),
        ("test.py", str(temp_repo / "test.py"), 3, "method_one", "def"),
        ("test.py", str(temp_repo / "test.py"), 6, "method_two", "def"),
        ("test.py", str(temp_repo / "test.py"), 9, "standalone_function", "def"),
    ]

    ranked_files = [("test.py", 0.9)]

    snippets = repomap.get_ranked_snippets(
        ranked_tags=ranked_tags,
        ranked_files=ranked_files,
        max_snippets_per_file=2,
    )

    # Should have at most 2 snippets for test.py
    if snippets:
        assert len(snippets[0]["snippets"]) <= 2


def test_snippet_token_cap(temp_repo):
    """Test per-snippet token cap."""
    available, _ = check_repomap_available(temp_repo)
    if not available:
        pytest.skip("RepoMap not available")

    repomap = HippoRepoMap(temp_repo, verbose=False)

    ranked_tags = [
        ("test.py", str(temp_repo / "test.py"), 2, "TestClass", "class"),
    ]

    ranked_files = [("test.py", 0.9)]

    snippets = repomap.get_ranked_snippets(
        ranked_tags=ranked_tags,
        ranked_files=ranked_files,
        per_snippet_token_cap=50,  # Small cap
    )

    # Each snippet should respect the cap
    for file_info in snippets:
        for snippet in file_info["snippets"]:
            assert snippet["tokens"] <= 50


def test_empty_input_handling(temp_repo):
    """Test handling of empty inputs."""
    available, _ = check_repomap_available(temp_repo)
    if not available:
        pytest.skip("RepoMap not available")

    repomap = HippoRepoMap(temp_repo, verbose=False)

    # Empty tags
    snippets = repomap.get_ranked_snippets(
        ranked_tags=[],
        ranked_files=[],
    )

    assert snippets == []


def test_repomap_exception_fallback(temp_repo):
    """Test exception handling in snippet extraction."""
    available, _ = check_repomap_available(temp_repo)
    if not available:
        pytest.skip("RepoMap not available")

    repomap = HippoRepoMap(temp_repo, verbose=False)

    # Mock render_tree to raise exception
    with patch.object(repomap.repomap, 'render_tree', side_effect=Exception("Test error")):
        ranked_tags = [
            ("test.py", str(temp_repo / "test.py"), 2, "TestClass", "class"),
        ]

        ranked_files = [("test.py", 0.9)]

        # Should not raise, just skip failed snippets
        snippets = repomap.get_ranked_snippets(
            ranked_tags=ranked_tags,
            ranked_files=ranked_files,
        )

        # Should return empty or partial results
        assert isinstance(snippets, list)


def test_deterministic_snippet_order(temp_repo):
    """Test that snippet order is deterministic."""
    available, _ = check_repomap_available(temp_repo)
    if not available:
        pytest.skip("RepoMap not available")

    repomap = HippoRepoMap(temp_repo, verbose=False)

    ranked_tags = [
        ("test.py", str(temp_repo / "test.py"), 2, "TestClass", "class"),
        ("utils.py", str(temp_repo / "utils.py"), 2, "helper_function", "def"),
    ]

    ranked_files = [
        ("test.py", 0.9),
        ("utils.py", 0.5),
    ]

    # Run twice
    snippets1 = repomap.get_ranked_snippets(
        ranked_tags=ranked_tags,
        ranked_files=ranked_files,
    )

    snippets2 = repomap.get_ranked_snippets(
        ranked_tags=ranked_tags,
        ranked_files=ranked_files,
    )

    # Should produce same order
    assert len(snippets1) == len(snippets2)
    if snippets1:
        assert [s["file"] for s in snippets1] == [s["file"] for s in snippets2]
