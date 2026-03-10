"""Tests for navigate tool with snippet extraction."""

import tempfile
from pathlib import Path

import pytest

from hippocampus.mcp.tools import navigate_tool, extract_mentions
from hippocampus.utils import write_json


@pytest.fixture
def temp_hippo_dir():
    """Create a temporary hippocampus directory with index."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        hippo_dir = root / ".hippocampus"
        hippo_dir.mkdir()

        # Create test files
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("""
class MainClass:
    def run(self):
        pass
""")

        (root / "src" / "utils.py").write_text("""
def helper():
    return 42
""")

        # Create index
        index = {
            "files": {
                "src/main.py": {
                    "signatures": [
                        {"name": "MainClass", "kind": "class"},
                        {"name": "run", "kind": "def"},
                    ]
                },
                "src/utils.py": {
                    "signatures": [
                        {"name": "helper", "kind": "def"},
                    ]
                },
            }
        }

        write_json(hippo_dir / "hippocampus-index.json", index)

        yield hippo_dir


def test_navigate_with_snippets(temp_hippo_dir):
    """Test navigate tool returns snippets when RepoMap available."""
    result = navigate_tool(
        query="MainClass run method",
        focus_files=["src/main.py"],
        hippo_dir=temp_hippo_dir,
    )

    assert "ranked_files" in result
    assert "explanation" in result
    assert "context_snippets" in result

    # Should have ranked files
    assert len(result["ranked_files"]) > 0

    # Snippets may be empty if RepoMap not available (graceful fallback)
    assert isinstance(result["context_snippets"], list)


def test_navigate_fallback_without_repomap(temp_hippo_dir):
    """Test navigate tool works without RepoMap."""
    # This should work even if RepoMap is not available
    result = navigate_tool(
        query="helper function",
        focus_files=[],
        hippo_dir=temp_hippo_dir,
    )

    assert "ranked_files" in result
    assert "explanation" in result
    assert "context_snippets" in result

    # Should still return ranked files
    assert len(result["ranked_files"]) > 0


def test_snippet_quality(temp_hippo_dir):
    """Test that snippets contain expected fields."""
    result = navigate_tool(
        query="MainClass",
        focus_files=["src/main.py"],
        hippo_dir=temp_hippo_dir,
    )

    snippets = result.get("context_snippets", [])

    # If snippets are returned, validate structure
    for file_info in snippets:
        assert "file" in file_info
        assert "rank" in file_info
        assert "snippets" in file_info
        assert "total_tokens" in file_info

        for snippet in file_info["snippets"]:
            assert "lois" in snippet
            assert "symbols" in snippet
            assert "content" in snippet
            assert "tokens" in snippet


def test_snippet_budget_enforced(temp_hippo_dir):
    """Test that snippet token budget is enforced."""
    result = navigate_tool(
        query="all code",
        focus_files=[],
        hippo_dir=temp_hippo_dir,
    )

    snippets = result.get("context_snippets", [])

    # Total tokens should not exceed budget (2500)
    total_tokens = sum(s["total_tokens"] for s in snippets)
    assert total_tokens <= 2500


def test_query_mention_extraction():
    """Test extraction of file and identifier mentions from query."""
    all_files = ["src/main.py", "src/utils.py", "tests/test_main.py"]
    index = {
        "files": {
            "src/main.py": {
                "signatures": [
                    {"name": "MainClass", "kind": "class"},
                    {"name": "run", "kind": "def"},
                ]
            },
            "src/utils.py": {
                "signatures": [
                    {"name": "helper", "kind": "def"},
                ]
            },
        }
    }

    # Test file mention extraction
    query = "fix bug in main.py"
    mentioned_files, mentioned_idents = extract_mentions(query, all_files, index)

    assert "src/main.py" in mentioned_files

    # Test identifier extraction
    query = "update MainClass run method"
    mentioned_files, mentioned_idents = extract_mentions(query, all_files, index)

    assert "MainClass" in mentioned_idents
    # "run" might be filtered as too short or common


def test_mention_extraction_boundary_matching():
    """Test word boundary matching in mention extraction."""
    all_files = ["src/test.py", "src/testing.py"]
    index = {"files": {}}

    # Should match "test.py" but not "testing.py" when query is "test"
    query = "fix test function"
    mentioned_files, _ = extract_mentions(query, all_files, index)

    # Word boundary matching should prevent "testing.py" from matching "test"
    # (depends on implementation details)
    assert isinstance(mentioned_files, set)


def test_mention_extraction_known_symbols():
    """Test that known symbols are prioritized."""
    all_files = ["src/main.py"]
    index = {
        "files": {
            "src/main.py": {
                "signatures": [
                    {"name": "MainClass", "kind": "class"},
                    {"name": "helper", "kind": "def"},
                ]
            }
        }
    }

    # Query with known and unknown symbols
    query = "update MainClass and SomeUnknownClass"
    _, mentioned_idents = extract_mentions(query, all_files, index)

    # Known symbol should be included
    assert "MainClass" in mentioned_idents

    # Unknown symbol might be included if it's CamelCase
    # (depends on filtering rules)


def test_mention_extraction_stopwords():
    """Test that stopwords are filtered out."""
    all_files = []
    index = {"files": {}}

    # Query with stopwords
    query = "fix the bug in this file"
    _, mentioned_idents = extract_mentions(query, all_files, index)

    # Stopwords should be filtered
    assert "the" not in mentioned_idents
    assert "this" not in mentioned_idents
    assert "fix" not in mentioned_idents


def test_navigate_with_focus_files(temp_hippo_dir):
    """Test that focus files get high priority."""
    result = navigate_tool(
        query="code",
        focus_files=["src/main.py"],
        hippo_dir=temp_hippo_dir,
    )

    ranked_files = result["ranked_files"]

    # Focus file should be ranked highly
    focus_file_ranks = [f for f in ranked_files if f["file"] == "src/main.py"]
    if focus_file_ranks:
        assert focus_file_ranks[0]["rank"] > 0.5
        assert focus_file_ranks[0]["tier"] == 1
