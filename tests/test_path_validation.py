"""Path validation security tests for Hippocampus.

Tests ensure that:
1. Absolute paths are rejected
2. Paths with .. components are rejected
3. Paths outside the repo root are rejected
4. Paths not in the index are rejected (when index_files provided)
"""

import pytest
from pathlib import Path
from hippocampus.tools.repomap_adapter import HippoRepoMap


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repo structure."""
    # Create some test files
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def main(): pass")
    (tmp_path / "src" / "utils.py").write_text("def helper(): pass")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("def test_main(): pass")

    return tmp_path


class TestPathValidation:
    """Test path validation in HippoRepoMap."""

    def test_rejects_absolute_paths(self, temp_repo):
        """Absolute paths should be rejected."""
        index_files = {"src/main.py", "src/utils.py"}
        repomap = HippoRepoMap(temp_repo, index_files=index_files)

        abs_path = str(temp_repo / "src" / "main.py")
        result = repomap._validate_repo_paths([abs_path])

        assert result == [], f"Absolute path should be rejected, got: {result}"

    def test_rejects_parent_dir_escape(self, temp_repo):
        """Paths with .. components should be rejected."""
        index_files = {"src/main.py", "src/utils.py"}
        repomap = HippoRepoMap(temp_repo, index_files=index_files)

        malicious_paths = [
            "../etc/passwd",
            "src/../../etc/passwd",
            "tests/../../../etc/passwd",
        ]

        for malicious in malicious_paths:
            result = repomap._validate_repo_paths([malicious])
            assert result == [], f"Path with .. should be rejected: {malicious}"

    def test_accepts_valid_relative_paths(self, temp_repo):
        """Valid relative paths should be accepted."""
        index_files = {"src/main.py", "src/utils.py", "tests/test_main.py"}
        repomap = HippoRepoMap(temp_repo, index_files=index_files)

        valid_paths = ["src/main.py", "src/utils.py", "tests/test_main.py"]
        result = repomap._validate_repo_paths(valid_paths)

        # Normalized to POSIX format
        assert set(result) == set(valid_paths)

    def test_filters_unknown_paths_when_index_provided(self, temp_repo):
        """When index_files is provided, unknown paths should be rejected."""
        index_files = {"src/main.py", "src/utils.py"}
        repomap = HippoRepoMap(temp_repo, index_files=index_files)

        paths = ["src/main.py", "unknown/file.py", "src/utils.py"]
        result = repomap._validate_repo_paths(paths)

        assert result == ["src/main.py", "src/utils.py"]

    def test_case_insensitive_matching(self, temp_repo):
        """Path matching should be case-insensitive."""
        # Use mixed case in index
        index_files = {"Src/Main.py", "SRC/UTILS.PY"}
        repomap = HippoRepoMap(temp_repo, index_files=index_files)

        # Query with different case
        paths = ["src/main.py", "SRC/utils.py"]
        result = repomap._validate_repo_paths(paths)

        assert len(result) == 2

    def test_rejects_paths_outside_root_after_resolution(self, temp_repo):
        """Paths that resolve outside the root should be rejected."""
        index_files = {"src/main.py"}
        repomap = HippoRepoMap(temp_repo, index_files=index_files)

        # This is a relative path that would resolve outside root
        # (if the repo structure didn't prevent it)
        outside_path = "../../../etc/passwd"
        result = repomap._validate_repo_paths([outside_path])

        assert result == []

    def test_empty_and_none_input(self, temp_repo):
        """Empty and None inputs should be handled gracefully."""
        repomap = HippoRepoMap(temp_repo)

        assert repomap._validate_repo_paths([]) == []
        assert repomap._validate_repo_paths([""]) == []
        # Empty strings and None filtered out, valid paths preserved
        assert repomap._validate_repo_paths(["", None, "src/main.py"]) == ["src/main.py"]

    def test_normalizes_path_separators(self, temp_repo):
        """Paths should be normalized to POSIX format."""
        index_files = {"src/main.py", "src/sub/nested/file.py"}
        repomap = HippoRepoMap(temp_repo, index_files=index_files)

        windows_path = "src\\sub\\nested\\file.py"
        result = repomap._validate_repo_paths([windows_path])

        assert result == ["src/sub/nested/file.py"]

    def test_get_ranked_tags_filters_paths(self, temp_repo):
        """get_ranked_tags should validate all input paths."""
        from unittest.mock import Mock, patch

        index_files = {"src/main.py", "src/utils.py"}
        repomap = HippoRepoMap(temp_repo, index_files=index_files)

        # Mock the Aider RepoMap to avoid actual parsing
        with patch.object(repomap.repomap, "get_ranked_tags", return_value=[]):
            # Call with malicious paths
            result = repomap.get_ranked_tags(
                chat_files=["src/main.py", "../etc/passwd"],
                other_files=["src/utils.py", "../../../secret.key"],
                mentioned_files={"src/main.py", "../../evil.py"},
            )

            # Should not raise exception - malicious paths filtered out silently
            assert result == []

    def test_no_index_files_allows_all_relative_paths(self, temp_repo):
        """When index_files is not provided, all relative paths within root are allowed."""
        # No index_files constraint
        repomap = HippoRepoMap(temp_repo)

        paths = ["src/main.py", "tests/test_main.py", "some/unknown/path.py"]
        result = repomap._validate_repo_paths(paths)

        # All relative paths without .. should pass
        assert len(result) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
