"""Tests for SymbolRanker functionality."""

from pathlib import Path
import pytest


def test_symbol_ranker_availability_check():
    """Test that is_repomap_available() correctly detects RepoMap availability."""
    from hippocampus.tools.ranker import is_repomap_available
    
    # Should return a boolean
    result = is_repomap_available()
    assert isinstance(result, bool)


def test_symbol_ranker_initialization():
    """Test that SymbolRanker can be initialized when dependencies are available."""
    from hippocampus.tools.ranker import is_repomap_available
    
    if not is_repomap_available():
        pytest.skip("RepoMap dependencies not available")
    
    from hippocampus.tools.ranker import SymbolRanker
    
    root = Path.cwd()
    ranker = SymbolRanker(root, verbose=False)
    
    assert ranker.root == root
    assert ranker.verbose is False


def test_symbol_ranker_rank_files_basic():
    """Test basic file ranking with SymbolRanker."""
    from hippocampus.tools.ranker import is_repomap_available
    
    if not is_repomap_available():
        pytest.skip("RepoMap dependencies not available")
    
    from hippocampus.tools.ranker import SymbolRanker
    
    root = Path.cwd()
    ranker = SymbolRanker(root, verbose=False)
    
    # Test with actual project files
    files = [
        "hippocampus/cli.py",
        "hippocampus/utils.py",
        "hippocampus/constants.py",
    ]
    
    ranked = ranker.rank_files(files)
    
    # Should return list of (file, score) tuples
    assert isinstance(ranked, list)
    assert len(ranked) == len(files)
    assert all(isinstance(item, tuple) and len(item) == 2 for item in ranked)
    assert all(isinstance(score, float) for _, score in ranked)
    
    # Scores should be positive
    assert all(score > 0 for _, score in ranked)


def test_symbol_ranker_focus_files():
    """Test that focus files are properly handled by SymbolRanker.

    Note: Due to hybrid scoring (60% symbol + 40% heuristic), focus files
    may not always have strictly higher scores, but they should be ranked
    reasonably high in the results.
    """
    from hippocampus.tools.ranker import is_repomap_available

    if not is_repomap_available():
        pytest.skip("RepoMap dependencies not available")

    from hippocampus.tools.ranker import SymbolRanker

    root = Path.cwd()
    ranker = SymbolRanker(root, verbose=False)

    files = [
        "hippocampus/cli.py",
        "hippocampus/utils.py",
        "hippocampus/constants.py",
    ]

    # Rank with focus on utils.py
    ranked_with_focus = ranker.rank_files(files, focus_files=["hippocampus/utils.py"])

    # Focus file should be in top 2 (allowing for hybrid scoring effects)
    ranked_files = [f for f, _ in ranked_with_focus]
    focus_position = ranked_files.index("hippocampus/utils.py")

    assert focus_position < 2, \
        f"Focus file should be in top 2, but was at position {focus_position}"


def test_symbol_ranker_deterministic():
    """Test that SymbolRanker produces deterministic results."""
    from hippocampus.tools.ranker import is_repomap_available
    
    if not is_repomap_available():
        pytest.skip("RepoMap dependencies not available")
    
    from hippocampus.tools.ranker import SymbolRanker
    
    root = Path.cwd()
    ranker = SymbolRanker(root, verbose=False)
    
    files = [
        "hippocampus/cli.py",
        "hippocampus/utils.py",
    ]
    
    # Run multiple times
    result1 = ranker.rank_files(files)
    result2 = ranker.rank_files(files)
    result3 = ranker.rank_files(files)
    
    # Results should be identical
    assert result1 == result2 == result3


def test_symbol_ranker_fallback_on_error():
    """Test that SymbolRanker gracefully handles errors."""
    from hippocampus.tools.ranker import is_repomap_available
    
    if not is_repomap_available():
        pytest.skip("RepoMap dependencies not available")
    
    from hippocampus.tools.ranker import SymbolRanker
    
    root = Path.cwd()
    ranker = SymbolRanker(root, verbose=False)
    
    # Test with non-existent files (should not crash)
    files = [
        "nonexistent/file1.py",
        "nonexistent/file2.py",
    ]
    
    # Should fall back gracefully and return heuristic scores
    ranked = ranker.rank_files(files)
    
    assert isinstance(ranked, list)
    assert len(ranked) == len(files)
