"""
Tag extraction for navigation plane.

Extracts both definitions and references from source files
using tree-sitter queries.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from ..parsers.ts_extract import Tag as TSTag, extract_tags
from ..parsers.lang_map import filename_to_lang


@dataclass
class Tag:
    """A code tag (definition or reference)."""
    rel_fname: str
    fname: str
    line: int
    name: str
    kind: str  # "def" or "ref"


def extract_tags_from_file(
    file_path: Path,
    root: Path,
    queries_dir: Path,
) -> Tuple[List[Tag], List[Tag]]:
    """
    Extract definitions and references from a single file.

    Args:
        file_path: Path to source file
        root: Repository root
        queries_dir: Path to tree-sitter queries directory

    Returns:
        Tuple of (definitions, references)
    """
    rel_path = str(file_path.relative_to(root))

    # Extract both definitions and references using tree-sitter
    ts_tags = extract_tags(str(file_path), rel_path, queries_dir)

    definitions = []
    references = []

    for tag in ts_tags:
        nav_tag = Tag(
            rel_fname=rel_path,
            fname=str(file_path),
            line=tag.line,
            name=tag.name,
            kind=tag.kind
        )

        if tag.kind == "def":
            definitions.append(nav_tag)
        elif tag.kind == "ref":
            references.append(nav_tag)

    return definitions, references


def extract_tags_batch(
    files: Set[str],
    root: Path,
    queries_dir: Path,
) -> Dict[str, Dict[str, List]]:
    """
    Extract tags from multiple files.

    Args:
        files: Set of file paths (relative to root)
        root: Repository root
        queries_dir: Path to tree-sitter queries directory

    Returns:
        Dict with "defines" and "references" keys mapping ident -> files
    """
    defines = defaultdict(list)
    references = defaultdict(list)

    for file_rel in files:
        file_path = root / file_rel
        if not file_path.exists():
            continue

        defs, refs = extract_tags_from_file(file_path, root, queries_dir)

        # Build defines map: ident -> [file1, file2, ...]
        for tag in defs:
            defines[tag.name].append(tag.rel_fname)

        # Build references map: ident -> [(file, line), ...]
        for tag in refs:
            references[tag.name].append((tag.rel_fname, tag.line))

    return {
        "defines": dict(defines),
        "references": dict(references)
    }


def extract_tags_cached(
    files: Set[str],
    root: Path,
    queries_dir: Path,
    refresh: str = "auto"
) -> Dict[str, Dict[str, List]]:
    """
    Extract tags with caching support.

    Args:
        files: Set of file paths
        root: Repository root
        queries_dir: Path to queries directory
        refresh: Cache refresh mode ("auto", "always", "manual")

    Returns:
        Dict with "defines" and "references"
    """
    # TODO: Implement mtime-based caching (Phase 5)
    # For now, always extract
    return extract_tags_batch(files, root, queries_dir)
