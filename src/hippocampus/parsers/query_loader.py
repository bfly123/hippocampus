"""Discovery and loading of .scm tree-sitter query files."""

from __future__ import annotations

from pathlib import Path

from ..constants import HIPPO_DIR, QUERIES_DIR

_QUERY_ALIASES = {
    "c_sharp": "csharp",
    "csharp": "c_sharp",
}


def find_queries_dir(project_root: Path) -> Path | None:
    """Find the queries directory under .hippocampus/."""
    queries = project_root / HIPPO_DIR / QUERIES_DIR
    if queries.is_dir():
        return queries
    return None


def load_query(queries_dir: Path, lang: str) -> str | None:
    """Load a .scm query file for the given language.

    Returns the query text or None if not found.
    """
    candidates = [lang]
    alias = _QUERY_ALIASES.get(lang)
    if alias:
        candidates.append(alias)

    for name in candidates:
        scm_path = queries_dir / f"{name}-tags.scm"
        if scm_path.exists():
            return scm_path.read_text(encoding="utf-8")
    return None


def available_languages(queries_dir: Path) -> list[str]:
    """List all languages with available .scm query files."""
    langs: set[str] = set()
    for scm in queries_dir.glob("*-tags.scm"):
        lang = scm.stem.replace("-tags", "")
        if lang == "csharp":
            lang = "c_sharp"
        langs.add(lang)
    return sorted(langs)
