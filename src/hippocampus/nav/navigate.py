"""Pure navigation function for direct import by llm-proxy.

Extracts the core logic from mcp/tools.py into a standalone function
that can be called without MCP infrastructure.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .navigate_mentions import extract_mentions
from .navigate_paths import validate_repo_paths
from ..utils import read_json


@dataclass
class NavigateResult:
    """Result of a navigate() call."""
    ranked_files: list[dict] = field(default_factory=list)
    snippets_text: str = ""
    snippet_tokens: int = 0


def navigate(
    query: str,
    focus_files: list[str] | None = None,
    conversation_files: list[str] | None = None,
    budget_tokens: int = 3000,
    hippo_dir: Path | None = None,
) -> NavigateResult:
    """Navigate codebase: rank files and extract relevant snippets.

    Pure function suitable for direct import by llm-proxy.
    Returns empty result on any error (fail-open).

    Args:
        query: Task description or search query.
        focus_files: Files explicitly in focus this turn.
        conversation_files: Accumulated files from cross-turn history.
        budget_tokens: Token budget for snippet extraction.
        hippo_dir: Path to .hippocampus directory.
    """
    try:
        return _navigate_inner(
            query, focus_files, conversation_files, budget_tokens, hippo_dir
        )
    except Exception as e:
        print(f"Warning: navigate() failed: {e}", file=sys.stderr)
        return NavigateResult()


def _navigate_inner(
    query: str,
    focus_files: list[str] | None,
    conversation_files: list[str] | None,
    budget_tokens: int,
    hippo_dir: Path | None,
) -> NavigateResult:
    """Core navigation logic (may raise)."""
    if hippo_dir is None:
        hippo_dir = Path.cwd() / ".hippocampus"

    # Index validation
    index_path = hippo_dir / "hippocampus-index.json"
    if not index_path.exists():
        return NavigateResult()

    index = read_json(index_path)
    root = hippo_dir.parent.resolve()
    all_files = list(index.get("files", {}).keys())
    if not all_files:
        return NavigateResult()

    # Merge focus_files + conversation_files and validate paths
    merged_focus_raw = list(focus_files or [])
    for f in (conversation_files or []):
        if f not in merged_focus_raw:
            merged_focus_raw.append(f)

    # Validate all paths are within the repo and exist in index
    merged_focus = validate_repo_paths(merged_focus_raw, set(all_files), root)

    # Extract mentions from query
    mentioned_files, mentioned_idents = extract_mentions(query, all_files, index)

    # Coarse ranking with GraphRanker
    from ..tools.ranker import is_repomap_available, GraphRanker

    coarse_ranker = GraphRanker(root, verbose=False)
    coarse_ranked = coarse_ranker.rank_files(
        files=all_files,
        focus_files=merged_focus,
        mentioned_files=mentioned_files,
    )

    # Fine ranking + snippet extraction with RepoMap
    context_snippets: list[dict] = []
    if is_repomap_available(root):
        try:
            context_snippets = _extract_snippets_repomap(
                root, coarse_ranked, merged_focus,
                mentioned_files, mentioned_idents, budget_tokens, all_files,
            )
        except Exception as e:
            print(f"Warning: RepoMap snippet extraction failed: {e}", file=sys.stderr)

    # Build ranked_files list
    ranked_files = []
    for f, r in coarse_ranked[:20]:
        tier = 1 if r > 0.5 else (2 if r > 0.2 else 3)
        ranked_files.append({"file": f, "rank": r, "tier": tier})

    # Render snippets
    snippets_text = ""
    snippet_tokens = 0
    if context_snippets:
        from .context_pack import render_snippets
        snippets_text = render_snippets(context_snippets)
        snippet_tokens = sum(s.get("total_tokens", 0) for s in context_snippets)

    return NavigateResult(
        ranked_files=ranked_files,
        snippets_text=snippets_text,
        snippet_tokens=snippet_tokens,
    )


def _extract_snippets_repomap(
    root: Path,
    coarse_ranked: list[tuple],
    merged_focus: list[str],
    mentioned_files: set[str],
    mentioned_idents: set[str],
    budget_tokens: int,
    all_files: list[str],
) -> list[dict]:
    """Extract code snippets using RepoMap (may raise)."""
    from ..tools.repomap_adapter import HippoRepoMap

    # Pass index_files to enable path validation
    repomap = HippoRepoMap(root, index_files=set(all_files))

    # Validate mentioned_files against repo root and index
    if mentioned_files:
        mentioned_files = set(
            validate_repo_paths(list(mentioned_files), set(all_files), root)
        )

    focus_set = set(merged_focus)
    top_files = [f for f, _ in coarse_ranked[:50]]
    all_files_for_ranking = list(focus_set.union(set(top_files)))
    mentioned_files_with_focus = mentioned_files.union(focus_set)

    ranked_tags = repomap.get_ranked_tags(
        chat_files=[],
        other_files=all_files_for_ranking,
        mentioned_files=mentioned_files_with_focus,
        mentioned_idents=mentioned_idents,
    )

    snippet_budget = min(max(budget_tokens, 100), 5000)
    per_snippet_cap = max(snippet_budget // 5, 50)

    return repomap.get_ranked_snippets(
        ranked_tags=ranked_tags,
        ranked_files=coarse_ranked[:20],
        max_snippets_per_file=2,
        global_token_budget=snippet_budget,
        per_snippet_token_cap=per_snippet_cap,
        mentioned_idents=mentioned_idents,
    )
