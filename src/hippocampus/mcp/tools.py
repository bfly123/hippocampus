"""Navigation-oriented MCP tool implementations for hippocampus."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..nav.navigate import extract_mentions
from ..utils import read_json


def _load_index(hippo_dir: Path) -> dict[str, Any] | None:
    index_path = hippo_dir / "hippocampus-index.json"
    if not index_path.exists():
        return None
    return read_json(index_path)


def _coarse_ranking(
    root: Path,
    *,
    all_files: list[str],
    focus_files: list[str],
    mentioned_files: set[str],
) -> list[tuple[str, float]]:
    from ..tools.ranker import GraphRanker

    return GraphRanker(root, verbose=False).rank_files(
        files=all_files,
        focus_files=focus_files,
        mentioned_files=mentioned_files,
    )


def _repomap_ranked_context(
    root: Path,
    *,
    all_files: list[str],
    focus_files: list[str],
    mentioned_files: set[str],
    mentioned_idents: set[str],
    budget_tokens: int,
) -> tuple[list[tuple[str, float]], list[dict[str, Any]]]:
    from ..tools.repomap_adapter import HippoRepoMap

    coarse_ranked = _coarse_ranking(
        root,
        all_files=all_files,
        focus_files=focus_files,
        mentioned_files=mentioned_files,
    )
    top_files = [file_path for file_path, _score in coarse_ranked[:50]]
    focus_set = set(focus_files)
    repomap = HippoRepoMap(root, index_files=set(all_files))
    ranked_tags = repomap.get_ranked_tags(
        chat_files=[],
        other_files=list(focus_set.union(set(top_files))),
        mentioned_files=mentioned_files.union(focus_set),
        mentioned_idents=mentioned_idents,
    )
    snippet_budget = min(max(budget_tokens, 100), 5000)
    snippets = repomap.get_ranked_snippets(
        ranked_tags=ranked_tags,
        ranked_files=coarse_ranked[:20],
        max_snippets_per_file=2,
        global_token_budget=snippet_budget,
        per_snippet_token_cap=max(snippet_budget // 5, 50),
        mentioned_idents=mentioned_idents,
    )
    return coarse_ranked, snippets


def _ranked_context(
    root: Path,
    *,
    all_files: list[str],
    focus_files: list[str],
    mentioned_files: set[str],
    mentioned_idents: set[str],
    budget_tokens: int,
) -> tuple[list[tuple[str, float]], list[dict[str, Any]]]:
    from ..tools.ranker import is_repomap_available
    import sys

    if not is_repomap_available(root):
        return _coarse_ranking(
            root,
            all_files=all_files,
            focus_files=focus_files,
            mentioned_files=mentioned_files,
        ), []
    try:
        return _repomap_ranked_context(
            root,
            all_files=all_files,
            focus_files=focus_files,
            mentioned_files=mentioned_files,
            mentioned_idents=mentioned_idents,
            budget_tokens=budget_tokens,
        )
    except Exception as exc:
        print(f"Warning: RepoMap snippet extraction failed: {exc}", file=sys.stderr)
        return _coarse_ranking(
            root,
            all_files=all_files,
            focus_files=focus_files,
            mentioned_files=mentioned_files,
        ), []


def _ranked_files_payload(ranked: list[tuple[str, float]]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for file_path, rank in ranked[:20]:
        tier = 1 if rank > 0.5 else 2 if rank > 0.2 else 3
        payload.append({"file": file_path, "rank": rank, "tier": tier})
    return payload


def navigate_tool(
    query: str,
    focus_files: list[str] | None = None,
    snapshot_ref: str | None = None,
    budget_tokens: int = 5000,
    hippo_dir: Path | None = None,
) -> dict[str, Any]:
    """Find relevant files and snippets for a task."""
    del snapshot_ref
    hippo_dir = hippo_dir or (Path.cwd() / ".hippocampus")
    root = hippo_dir.parent.resolve()
    index = _load_index(hippo_dir)
    if index is None:
        return {"error": "Index not found. Run 'hippo index' first."}

    all_files = list(index.get("files", {}))
    mentioned_files, mentioned_idents = extract_mentions(query, all_files, index)
    ranked, context_snippets = _ranked_context(
        root,
        all_files=all_files,
        focus_files=focus_files or [],
        mentioned_files=mentioned_files,
        mentioned_idents=mentioned_idents,
        budget_tokens=budget_tokens,
    )
    return {
        "ranked_files": _ranked_files_payload(ranked),
        "explanation": f"Found {len(ranked)} files, showing top 20",
        "context_snippets": context_snippets,
    }
