"""Token estimation, JSON I/O, and path utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import CHARS_PER_TOKEN


def estimate_tokens(text: str) -> int:
    """Estimate token count from character length."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def read_json(path: Path) -> Any:
    """Read and parse a JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any, indent: int = 2) -> None:
    """Write data as formatted JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def write_text(path: Path, text: str) -> None:
    """Write text to a file, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def relative_path(base: Path, target: Path) -> str:
    """Get relative path string from base to target."""
    try:
        return str(target.relative_to(base))
    except ValueError:
        return str(target)


def is_hidden(path: Path) -> bool:
    """Check if any component of the path starts with a dot."""
    return any(part.startswith(".") for part in path.parts)


_RUNTIME_ARTIFACT_NAMES = frozenset(
    {
        "opencode.json",
        "latest-context.json",
        "latest-context-history.jsonl",
        "repomix-compress-trimmed.json",
        "hippocampus-index.json",
        "hippocampus-viz.html",
        "code-signatures.json",
        "architect-metrics.json",
        "phase1-cache.json",
        "phase2-cache.json",
        "phase3-cache.json",
        "tag-vocab.json",
        "tree.json",
        "tree-diff.json",
        "structure-prompt.md",
    }
)
_RUNTIME_ARTIFACT_DIRS = frozenset(
    {
        ".hippocampus",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".aider.tags.cache.v4",
        "snapshots",
        "dist",
        "build",
    }
)


def is_runtime_artifact(path: Path) -> bool:
    """Check whether a path is a generated/runtime artifact, not source structure."""
    normalized = Path(path)
    if any(part in _RUNTIME_ARTIFACT_DIRS for part in normalized.parts):
        return True
    name = normalized.name
    if name in _RUNTIME_ARTIFACT_NAMES:
        return True
    if name.endswith("-viz.html"):
        return True
    if name.startswith("latest-context") and normalized.suffix in {".json", ".jsonl"}:
        return True
    return False


# File stems (case-insensitive) that are always project docs.
_DOC_NAMES = frozenset({
    "readme", "changelog", "changes", "license", "licence",
    "authors", "contributors", "copying", "notice",
})

# Directories whose contents are treated as documentation.
_DOC_DIRS = frozenset({"plans"})

# Extensions that are always documentation (non-markdown).
_DOC_EXTS_ALWAYS = frozenset({".rst", ".adoc", ".txt"})


def is_doc(path: Path) -> bool:
    """Check if a file is a documentation/non-source file.

    Excludes: README, CHANGELOG, LICENSE (any ext), plans/*.md,
              and .rst/.adoc/.txt files.
    Keeps: functional .md like SKILL.md.
    """
    stem = path.stem.upper()
    suffix = path.suffix.lower()
    # Known doc names (prefix match to catch README_zh, CHANGELOG_4.0, etc.)
    if any(stem.startswith(n.upper()) for n in _DOC_NAMES):
        return True
    # Non-markdown doc extensions
    if suffix in _DOC_EXTS_ALWAYS:
        return True
    # .md files inside doc directories (e.g. plans/)
    if suffix == ".md" and any(
        part.lower() in _DOC_DIRS for part in path.parts[:-1]
    ):
        return True
    return False
