"""Structure tree diff generator — compares two tree.json files."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..types import DiffEntry, TreeDiffDoc, TreeNode
from ..utils import read_json, write_json


def _flatten_tree(node: TreeNode, out: dict[str, TreeNode] | None = None) -> dict[str, TreeNode]:
    """Flatten a tree into a dict keyed by node id."""
    if out is None:
        out = {}
    out[node.id] = node
    for child in node.children:
        _flatten_tree(child, out)
    return out


def compute_diff(
    baseline: TreeNode,
    current: TreeNode,
) -> list[DiffEntry]:
    """Compare two trees and return a list of changes."""
    old_map = _flatten_tree(baseline)
    new_map = _flatten_tree(current)

    changes: list[DiffEntry] = []

    # Detect removed nodes
    for nid, node in old_map.items():
        if nid not in new_map:
            changes.append(DiffEntry(
                id=nid, type=node.type,
                name=node.name, change="removed",
            ))

    # Detect added nodes
    for nid, node in new_map.items():
        if nid not in old_map:
            changes.append(DiffEntry(
                id=nid, type=node.type,
                name=node.name, change="added",
            ))

    # Detect modified (children changed)
    for nid in old_map:
        if nid in new_map:
            old_children = {c.id for c in old_map[nid].children}
            new_children = {c.id for c in new_map[nid].children}
            if old_children != new_children:
                node = new_map[nid]
                changes.append(DiffEntry(
                    id=nid, type=node.type,
                    name=node.name, change="modified",
                ))

    return changes


def run_tree_diff(
    output_dir: Path,
    baseline_path: Path | None = None,
    current_path: Path | None = None,
    verbose: bool = False,
) -> TreeDiffDoc | None:
    """Generate tree-diff.json by comparing baseline and current tree.json."""
    from ..constants import TREE_FILE, TREE_DIFF_FILE

    if current_path is None:
        current_path = output_dir / TREE_FILE
    if not current_path.exists():
        raise FileNotFoundError(f"Current tree not found: {current_path}")

    # Load current tree
    current_data = read_json(current_path)
    current_root = TreeNode(**current_data["root"])

    # Find baseline
    if baseline_path is None:
        baseline_path = output_dir / "tree-baseline.json"
    if not baseline_path.exists():
        return None  # No baseline, skip diff

    baseline_data = read_json(baseline_path)
    baseline_root = TreeNode(**baseline_data["root"])

    changes = compute_diff(baseline_root, current_root)
    doc = TreeDiffDoc(
        generated_at=datetime.now(timezone.utc).isoformat(),
        baseline_at=baseline_data.get("generated_at", ""),
        changes=changes,
    )

    out_path = output_dir / TREE_DIFF_FILE
    write_json(out_path, doc.model_dump())
    return doc
