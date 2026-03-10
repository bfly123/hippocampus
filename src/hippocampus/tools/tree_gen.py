"""Structure tree generator — parses repomix directoryStructure into tree.json."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..types import TreeDoc, TreeNode
from ..utils import write_json


def _parse_indent(line: str) -> tuple[int, str]:
    """Return (indent_level, stripped_name) from a directory structure line."""
    stripped = line.rstrip()
    if not stripped:
        return -1, ""
    indent = len(stripped) - len(stripped.lstrip())
    name = stripped.lstrip()
    return indent // 2, name


def _is_dir_entry(name: str) -> bool:
    """Check if a directory structure entry is a directory."""
    return name.endswith("/")


def parse_directory_structure(text: str) -> TreeNode:
    """Parse repomix directoryStructure text into a TreeNode tree."""
    root = TreeNode(id="dir:.", type="dir", name=".")
    stack: list[tuple[int, TreeNode]] = [(-1, root)]

    for line in text.splitlines():
        level, name = _parse_indent(line)
        if level < 0 or not name:
            continue

        is_dir = _is_dir_entry(name)
        clean_name = name.rstrip("/")

        # Pop stack to find parent
        while stack and stack[-1][0] >= level:
            stack.pop()

        parent = stack[-1][1] if stack else root

        # Build path from stack
        path_parts = [s[1].name for s in stack[1:]] + [clean_name]
        rel_path = "/".join(path_parts)

        node_type = "dir" if is_dir else "file"
        node_id = f"{node_type}:{rel_path}"

        node = TreeNode(id=node_id, type=node_type, name=clean_name)
        parent.children.append(node)

        if is_dir:
            stack.append((level, node))

    return root


def run_tree_gen(
    target: Path,
    output_dir: Path,
    structure_json: dict | None = None,
    verbose: bool = False,
) -> TreeDoc:
    """Generate tree.json from repomix directoryStructure.

    If structure_json is provided, uses it directly.
    Otherwise runs repomix to get the structure.
    """
    if structure_json is None:
        from ..repomix.runner import run_repomix_structure
        import tempfile
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False
        ) as tmp:
            tmp_path = Path(tmp.name)
        try:
            structure_json = run_repomix_structure(target, tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    dir_text = structure_json.get("directoryStructure", "")
    if not dir_text:
        raise ValueError("No directoryStructure found in repomix output")

    root = parse_directory_structure(dir_text)
    doc = TreeDoc(
        generated_at=datetime.now(timezone.utc).isoformat(),
        root=root,
    )

    from ..constants import TREE_FILE
    out_path = output_dir / TREE_FILE
    write_json(out_path, doc.model_dump())
    return doc
