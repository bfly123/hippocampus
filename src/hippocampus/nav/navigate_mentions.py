from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple


_STOPWORDS = {
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "should",
    "can", "could", "may", "might", "must", "this", "that", "these", "those",
    "fix", "bug", "add", "update", "remove", "delete", "create", "implement",
}


def extract_mentions(
    query: str,
    all_files: list[str],
    index: dict,
) -> Tuple[set[str], set[str]]:
    known_symbols, known_symbols_lower = _collect_known_symbols(index=index)
    query_lower = query.lower()
    mentioned_files = _extract_file_mentions(query_lower=query_lower, all_files=all_files)

    mentioned_idents: set[str] = set()
    for ident in _identifier_candidates(query=query):
        if _is_known_symbol(ident, known_symbols, known_symbols_lower):
            mentioned_idents.add(ident)
            continue
        if _is_generic_noise(ident):
            continue
        if _looks_like_identifier(ident):
            mentioned_idents.add(ident)

    return mentioned_files, mentioned_idents


def _collect_known_symbols(index: dict) -> tuple[set[str], set[str]]:
    symbols: set[str] = set()
    symbols_lower: set[str] = set()
    files = index.get("files", {}) if isinstance(index.get("files", {}), dict) else {}
    for file_info in files.values():
        signatures = (
            file_info.get("signatures", [])
            if isinstance(file_info, dict)
            else []
        )
        for signature in signatures:
            name = signature.get("name", "") if isinstance(signature, dict) else ""
            if not name:
                continue
            symbols.add(name)
            symbols_lower.add(name.lower())
    return symbols, symbols_lower


def _extract_file_mentions(*, query_lower: str, all_files: list[str]) -> set[str]:
    out: set[str] = set()
    for file in all_files:
        stem = Path(file).stem.lower()
        if re.search(r"\b" + re.escape(stem) + r"\b", query_lower):
            out.add(file)
    return out


def _identifier_candidates(*, query: str) -> list[str]:
    pattern = r"\b[A-Z][a-zA-Z0-9_]*\b|\b[a-z_][a-z0-9_]+\b"
    return re.findall(pattern, query)


def _is_known_symbol(ident: str, symbols: set[str], symbols_lower: set[str]) -> bool:
    return ident in symbols or ident.lower() in symbols_lower


def _is_generic_noise(ident: str) -> bool:
    if ident.lower() in _STOPWORDS:
        return True
    if len(ident) < 3:
        return True
    if ident.isdigit():
        return True
    return False


def _looks_like_identifier(ident: str) -> bool:
    return ident[0].isupper() or len(ident) > 5
