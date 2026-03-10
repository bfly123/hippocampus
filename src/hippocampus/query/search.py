"""hippo_search — tag/keyword search across indexed files.

Supports three search modes:
  - tags only: intersection match against file tags
  - pattern only: case-insensitive substring match on filepath/desc/signatures
  - combined: weighted blend of both scores

Usage:
  result = build_search(index, tags=["api", "python"], pattern="route", limit=10)
  print(result["content"])
"""

from __future__ import annotations

from typing import Any

from ..utils import estimate_tokens


def _tag_score(query_tags: list[str], file_tags: list[str]) -> float:
    """Score based on tag intersection.

    Returns |intersection| / |query_tags|, or 0.0 if no query tags.
    """
    if not query_tags:
        return 0.0
    query_set = set(query_tags)
    file_set = set(file_tags)
    return len(query_set & file_set) / len(query_set)


def _pattern_score(pattern: str, filepath: str, file_data: dict) -> float:
    """Score based on case-insensitive substring matching.

    Priority: filepath/filename (1.0) > desc (0.7) > signature name (0.5).
    Returns 0.0 if no pattern or no match.
    """
    if not pattern:
        return 0.0
    p = pattern.lower()

    # Check filepath (includes filename)
    if p in filepath.lower():
        return 1.0

    # Check description
    desc = file_data.get("desc", "")
    if desc and p in desc.lower():
        return 0.7

    # Check signature names
    for sig in file_data.get("signatures", []):
        name = sig.get("name", "")
        if name and p in name.lower():
            return 0.5

    return 0.0


def _combined_score(
    query_tags: list[str] | None,
    pattern: str | None,
    filepath: str,
    file_data: dict,
) -> float:
    """Compute combined search score.

    Both present: 0.6 * tag_score + 0.4 * pattern_score
    Tags only:    tag_score
    Pattern only: pattern_score
    """
    tags = query_tags or []
    pat = pattern or ""

    has_tags = len(tags) > 0
    has_pattern = len(pat.strip()) > 0

    file_tags = file_data.get("tags", [])
    ts = _tag_score(tags, file_tags) if has_tags else 0.0
    ps = _pattern_score(pat, filepath, file_data) if has_pattern else 0.0

    if has_tags and has_pattern:
        return 0.6 * ts + 0.4 * ps
    if has_tags:
        return ts
    return ps


def _render_matches(
    matches: list[dict],
    query_tags: list[str] | None,
    pattern: str | None,
) -> str:
    """Render search results as Markdown."""
    lines = ["# Search Results", ""]

    # Query summary
    parts = []
    if query_tags:
        parts.append(f"tags: {', '.join(query_tags)}")
    if pattern:
        parts.append(f"pattern: \"{pattern}\"")
    lines.append(f"Query: {' | '.join(parts)}")
    lines.append(f"Matches: {len(matches)}")
    lines.append("")

    if not matches:
        lines.append("_No matching files found._")
        lines.append("")
        return "\n".join(lines)

    for m in matches:
        tags_str = f" [{', '.join(m['tags'])}]" if m.get("tags") else ""
        mod_str = f" ({m['module']})" if m.get("module") else ""
        lines.append(
            f"- `{m['path']}` **{m['score']:.2f}**{mod_str}{tags_str}: {m['desc']}"
        )
    lines.append("")
    return "\n".join(lines)


def build_search(
    index: dict[str, Any],
    tags: list[str] | None = None,
    pattern: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search indexed files by tags and/or keyword pattern.

    Args:
        index: The hippocampus index dict.
        tags: Tag names to match (intersection).
        pattern: Case-insensitive substring to search.
        limit: Maximum number of results.

    Returns dict with:
        matches: list[dict]     — scored results
        consumed_tokens: int    — estimated tokens used
        content: str            — Markdown text
    """
    files = index.get("files", {})
    scored: list[tuple[float, str, dict]] = []

    for filepath, file_data in files.items():
        score = _combined_score(tags, pattern, filepath, file_data)
        if score > 0.0:
            scored.append((score, filepath, file_data))

    # Sort by score descending, then path ascending for stability
    scored.sort(key=lambda x: (-x[0], x[1]))
    scored = scored[:limit]

    matches = [
        {
            "path": filepath,
            "desc": fd.get("desc", ""),
            "score": score,
            "tags": fd.get("tags", []),
            "module": fd.get("module", ""),
        }
        for score, filepath, fd in scored
    ]

    content = _render_matches(matches, tags, pattern)
    consumed = estimate_tokens(content)

    return {
        "matches": matches,
        "consumed_tokens": consumed,
        "content": content,
    }
