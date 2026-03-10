"""Tests for hippocampus.tools.tree_diff — tree comparison logic."""

from __future__ import annotations

from hippocampus.tools.tree_diff import _flatten_tree, compute_diff
from hippocampus.types import DiffEntry, TreeNode


class TestFlattenTree:
    def test_single_node(self):
        node = TreeNode(id="dir:.", type="dir", name=".")
        flat = _flatten_tree(node)
        assert len(flat) == 1
        assert "dir:." in flat

    def test_nested_tree(self):
        root = TreeNode(
            id="dir:.", type="dir", name=".",
            children=[
                TreeNode(id="dir:src", type="dir", name="src", children=[
                    TreeNode(id="file:src/a.py", type="file", name="a.py"),
                ]),
                TreeNode(id="file:README.md", type="file", name="README.md"),
            ],
        )
        flat = _flatten_tree(root)
        assert len(flat) == 4
        assert "file:src/a.py" in flat
        assert "file:README.md" in flat


class TestComputeDiff:
    def _make_baseline(self):
        return TreeNode(
            id="dir:.", type="dir", name=".",
            children=[
                TreeNode(id="dir:src", type="dir", name="src", children=[
                    TreeNode(id="file:src/a.py", type="file", name="a.py"),
                    TreeNode(id="file:src/b.py", type="file", name="b.py"),
                ]),
                TreeNode(id="file:README.md", type="file", name="README.md"),
            ],
        )

    def test_identical_trees_no_changes(self):
        tree = self._make_baseline()
        changes = compute_diff(tree, tree)
        assert len(changes) == 0

    def test_detect_added_file(self):
        baseline = self._make_baseline()
        current = TreeNode(
            id="dir:.", type="dir", name=".",
            children=[
                TreeNode(id="dir:src", type="dir", name="src", children=[
                    TreeNode(id="file:src/a.py", type="file", name="a.py"),
                    TreeNode(id="file:src/b.py", type="file", name="b.py"),
                    TreeNode(id="file:src/c.py", type="file", name="c.py"),
                ]),
                TreeNode(id="file:README.md", type="file", name="README.md"),
            ],
        )
        changes = compute_diff(baseline, current)
        added = [c for c in changes if c.change == "added"]
        assert any(c.id == "file:src/c.py" for c in added)

    def test_detect_removed_file(self):
        baseline = self._make_baseline()
        current = TreeNode(
            id="dir:.", type="dir", name=".",
            children=[
                TreeNode(id="dir:src", type="dir", name="src", children=[
                    TreeNode(id="file:src/a.py", type="file", name="a.py"),
                ]),
                TreeNode(id="file:README.md", type="file", name="README.md"),
            ],
        )
        changes = compute_diff(baseline, current)
        removed = [c for c in changes if c.change == "removed"]
        assert any(c.id == "file:src/b.py" for c in removed)
