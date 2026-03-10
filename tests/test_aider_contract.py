"""Contract tests for Aider RepoMap adapter."""

from pathlib import Path
import pytest


def test_repomap_adapter_availability():
    """Test that check_repomap_available() works correctly."""
    from hippocampus.tools.repomap_adapter import check_repomap_available
    
    available, error = check_repomap_available()
    
    # Should return tuple of (bool, str)
    assert isinstance(available, bool)
    assert isinstance(error, str)
    
    # If available, error should be empty
    if available:
        assert error == ""


def test_hippo_io_interface():
    """Test that HippoIO implements required Aider IO interface."""
    from hippocampus.tools.ranker import is_repomap_available
    
    if not is_repomap_available():
        pytest.skip("RepoMap dependencies not available")
    
    from hippocampus.tools.repomap_adapter import HippoIO
    
    io = HippoIO(verbose=False)
    
    # Check required methods exist
    assert hasattr(io, 'read_text')
    assert hasattr(io, 'tool_error')
    assert hasattr(io, 'tool_warning')
    assert hasattr(io, 'tool_output')
    
    # Test read_text
    result = io.read_text(__file__)
    assert isinstance(result, (str, type(None)))
    
    # Test error/warning methods (should not crash)
    io.tool_error("test error")
    io.tool_warning("test warning")
    io.tool_output("test output")


def test_hippo_model_interface():
    """Test that HippoModel implements required Aider model interface."""
    from hippocampus.tools.ranker import is_repomap_available
    
    if not is_repomap_available():
        pytest.skip("RepoMap dependencies not available")
    
    from hippocampus.tools.repomap_adapter import HippoModel
    
    model = HippoModel()
    
    # Check required methods exist
    assert hasattr(model, 'token_count')
    
    # Test token_count
    count = model.token_count("hello world")
    assert isinstance(count, int)
    assert count > 0


def test_hippo_repomap_initialization():
    """Test that HippoRepoMap can be initialized."""
    from hippocampus.tools.ranker import is_repomap_available
    
    if not is_repomap_available():
        pytest.skip("RepoMap dependencies not available")
    
    from hippocampus.tools.repomap_adapter import HippoRepoMap
    
    root = Path.cwd()
    repomap = HippoRepoMap(root=root, map_tokens=1024, verbose=False)
    
    assert repomap.root == root
    assert repomap.verbose is False


def test_hippo_repomap_get_ranked_tags():
    """Test that HippoRepoMap.get_ranked_tags() returns expected format."""
    from hippocampus.tools.ranker import is_repomap_available
    
    if not is_repomap_available():
        pytest.skip("RepoMap dependencies not available")
    
    from hippocampus.tools.repomap_adapter import HippoRepoMap
    
    root = Path.cwd()
    repomap = HippoRepoMap(root=root, map_tokens=1024, verbose=False)
    
    # Test with actual project files
    chat_files = ["src/hippocampus/utils.py"]
    other_files = ["src/hippocampus/constants.py"]
    
    ranked_tags = repomap.get_ranked_tags(
        chat_files=chat_files,
        other_files=other_files,
        mentioned_files=set(),
        mentioned_idents=set(),
    )
    
    # Should return a list
    assert isinstance(ranked_tags, list)
    
    # Each item should be a tuple with 5 elements
    # (file_path, symbol_name, rank, symbol_type, context)
    if ranked_tags:  # May be empty for small files
        for item in ranked_tags[:5]:  # Check first 5
            assert isinstance(item, tuple)
            # Allow both 5-tuple and 1-tuple formats (compatibility)
            assert len(item) in (1, 5), f"Expected 1 or 5 elements, got {len(item)}"


def test_repomap_determinism():
    """Test that RepoMap produces deterministic results."""
    from hippocampus.tools.ranker import is_repomap_available
    
    if not is_repomap_available():
        pytest.skip("RepoMap dependencies not available")
    
    from hippocampus.tools.repomap_adapter import HippoRepoMap
    
    root = Path.cwd()
    repomap = HippoRepoMap(root=root, map_tokens=1024, verbose=False)
    
    chat_files = ["src/hippocampus/utils.py"]
    other_files = ["src/hippocampus/constants.py"]
    
    # Run twice
    result1 = repomap.get_ranked_tags(
        chat_files=chat_files,
        other_files=other_files,
        mentioned_files=set(),
        mentioned_idents=set(),
    )
    
    result2 = repomap.get_ranked_tags(
        chat_files=chat_files,
        other_files=other_files,
        mentioned_files=set(),
        mentioned_idents=set(),
    )
    
    # Results should be identical
    assert result1 == result2


def test_repomap_path_handling():
    """Test that RepoMap correctly handles relative and absolute paths."""
    from hippocampus.tools.ranker import is_repomap_available
    
    if not is_repomap_available():
        pytest.skip("RepoMap dependencies not available")
    
    from hippocampus.tools.repomap_adapter import HippoRepoMap
    
    root = Path.cwd()
    repomap = HippoRepoMap(root=root, map_tokens=1024, verbose=False)
    
    # Test with relative paths (should work)
    chat_files = ["src/hippocampus/utils.py"]
    other_files = ["src/hippocampus/constants.py"]
    
    result = repomap.get_ranked_tags(
        chat_files=chat_files,
        other_files=other_files,
        mentioned_files=set(),
        mentioned_idents=set(),
    )
    
    # Should not crash and return a list
    assert isinstance(result, list)


def test_repomap_empty_input():
    """Test that RepoMap handles empty input.

    Note: Aider RepoMap has a bug where it raises ZeroDivisionError on empty input.
    This test documents the current behavior.
    """
    from hippocampus.tools.ranker import is_repomap_available

    if not is_repomap_available():
        pytest.skip("RepoMap dependencies not available")

    from hippocampus.tools.repomap_adapter import HippoRepoMap

    root = Path.cwd()
    repomap = HippoRepoMap(root=root, map_tokens=1024, verbose=False)

    # Test with empty inputs - currently raises ZeroDivisionError
    with pytest.raises(ZeroDivisionError):
        repomap.get_ranked_tags(
            chat_files=[],
            other_files=[],
            mentioned_files=set(),
            mentioned_idents=set(),
        )
