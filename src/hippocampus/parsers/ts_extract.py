"""Tree-sitter parsing and tag extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .lang_map import detect_file_language
from .query_loader import load_query


def _normalize_query_for_runtime(lang: str, query_scm: str) -> str:
    """Patch known legacy query/node mismatches for current parser backend."""
    # Legacy javascript tags use "(function)" while newer grammar uses
    # "(function_expression)". Keep existing query files usable.
    if lang == "javascript" and "(function)" in query_scm:
        query_scm = query_scm.replace("(function)", "(function_expression)")
    return query_scm


@dataclass
class Tag:
    """A code tag extracted by tree-sitter."""
    rel_fname: str
    fname: str
    name: str
    kind: str  # "def" or "ref"
    line: int
    tag_type: str = ""  # e.g. "class", "function"


def _get_parser_and_language(lang: str):
    """Get tree-sitter parser and language for a given language name."""
    lang_name = lang.replace("-", "_")

    # Use tree-sitter-language-pack (compatible with tree-sitter 0.25.x)
    try:
        from tree_sitter_language_pack import get_language, get_parser
        ts_lang = get_language(lang_name)
        parser = get_parser(lang_name)
        return parser, ts_lang
    except Exception:
        pass

    # Fallback: try tree_sitter_languages (older versions)
    try:
        from tree_sitter_languages import get_language, get_parser
        ts_lang = get_language(lang_name)
        parser = get_parser(lang_name)
        return parser, ts_lang
    except Exception:
        pass

    return None, None


def extract_tags(
    fname: str,
    rel_fname: str,
    queries_dir: Path,
) -> list[Tag]:
    """Extract definition tags from a source file using tree-sitter.

    Returns a list of Tag objects for definitions found in the file.
    """
    lang = detect_file_language(fname)
    if not lang:
        return []

    parser, ts_lang = _get_parser_and_language(lang)
    if parser is None or ts_lang is None:
        return []

    query_scm = load_query(queries_dir, lang)
    if not query_scm:
        return []
    query_scm = _normalize_query_for_runtime(lang, query_scm)

    try:
        code = Path(fname).read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return []

    if not code:
        return []

    tree = parser.parse(bytes(code, "utf-8"))

    # Create query - use Query constructor for tree-sitter 0.25.x
    import tree_sitter
    query = tree_sitter.Query(ts_lang, query_scm)

    # Execute query with compatibility for both old and new API
    try:
        # Try new API (tree-sitter 0.25.x): QueryCursor
        cursor = tree_sitter.QueryCursor(query)
        matches = cursor.matches(tree.root_node)
        # matches returns list[(pattern_index, captures_dict)]
        # Aggregate all captures
        captures = {}
        for pattern_index, match_captures in matches:
            for capture_name, nodes in match_captures.items():
                if capture_name not in captures:
                    captures[capture_name] = []
                captures[capture_name].extend(nodes)
    except (AttributeError, TypeError):
        # Fallback to old API (tree-sitter < 0.25): query.captures()
        captures = query.captures(tree.root_node)

    tags = []
    # tree-sitter 0.23+ returns dict[str, list[Node]]
    if isinstance(captures, dict):
        all_nodes = []
        for tag_name, nodes in captures.items():
            all_nodes += [(node, tag_name) for node in nodes]
    else:
        all_nodes = list(captures)

    for node, tag_name in all_nodes:
        if tag_name.startswith("name.definition."):
            kind = "def"
            tag_type = tag_name.replace("name.definition.", "")
        elif tag_name.startswith("name.reference."):
            kind = "ref"
            tag_type = tag_name.replace("name.reference.", "")
        else:
            continue

        tags.append(Tag(
            rel_fname=rel_fname,
            fname=fname,
            name=node.text.decode("utf-8"),
            kind=kind,
            line=node.start_point[0],
            tag_type=tag_type,
        ))

    return tags


def extract_definitions(
    fname: str,
    rel_fname: str,
    queries_dir: Path,
) -> list[Tag]:
    """Extract only definition tags (no references)."""
    return [t for t in extract_tags(fname, rel_fname, queries_dir)
            if t.kind == "def"]
