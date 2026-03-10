"""Navigation-oriented MCP tool implementations for hippocampus."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..nav.navigate import extract_mentions
from ..utils import read_json


def navigate_tool(
    query: str,
    focus_files: Optional[List[str]] = None,
    snapshot_ref: Optional[str] = None,
    budget_tokens: int = 5000,
    hippo_dir: Path = None,
) -> Dict[str, Any]:
    """
    Navigate tool: find relevant files/symbols for a task.
    
    Args:
        query: Task description or query
        focus_files: Files currently in focus
        snapshot_ref: Snapshot reference
        budget_tokens: Token budget for context
        hippo_dir: Hippocampus directory
    
    Returns:
        Navigation results with ranked files and context
    """
    if hippo_dir is None:
        hippo_dir = Path.cwd() / ".hippocampus"

    # Derive root path from hippo_dir (project root is parent of .hippocampus)
    root = hippo_dir.parent.resolve()

    # Load index
    index_path = hippo_dir / "hippocampus-index.json"
    if not index_path.exists():
        return {"error": "Index not found. Run 'hippo index' first."}
    
    index = read_json(index_path)

    # Extract all files from index (use files dict directly)
    all_files = list(index.get("files", {}).keys())

    # Extract mentions from query
    mentioned_files, mentioned_idents = extract_mentions(query, all_files, index)

    # Strategy: Use GraphRanker for coarse ranking, then RepoMap for fine ranking + snippets
    from ..tools.ranker import is_repomap_available, GraphRanker

    context_snippets = []

    if is_repomap_available(root):
        # Step 1: Coarse ranking with GraphRanker
        coarse_ranker = GraphRanker(root, verbose=False)
        coarse_ranked = coarse_ranker.rank_files(
            files=all_files,
            focus_files=focus_files or [],
            mentioned_files=mentioned_files
        )

        # Take top-50 files for RepoMap processing
        top_files = [f for f, _ in coarse_ranked[:50]]

        # Step 2: Fine ranking + snippet extraction with RepoMap
        try:
            from ..tools.repomap_adapter import HippoRepoMap

            # Pass index_files to enable path validation at adapter level
            repomap = HippoRepoMap(root, index_files=set(all_files))

            # CRITICAL FIX: Don't pass focus_files as chat_files
            # Aider excludes chat_files from ranked tags (repomap.py:537)
            # Instead, pass focus files in other_files + mentioned_files
            focus_set = set(focus_files or [])

            # Combine focus files with top files, ensuring focus files are included
            all_files_for_ranking = list(focus_set.union(set(top_files)))

            # Add focus files to mentioned_files to boost their ranking
            mentioned_files_with_focus = mentioned_files.union(focus_set)

            # Single RepoMap call: get ranked tags
            # Pass empty chat_files to avoid exclusion
            ranked_tags = repomap.get_ranked_tags(
                chat_files=[],  # Empty to avoid Aider's exclusion logic
                other_files=all_files_for_ranking,
                mentioned_files=mentioned_files_with_focus,
                mentioned_idents=mentioned_idents
            )

            # Keep coarse ranking as authoritative (avoid re-ranking)
            ranked = coarse_ranked

            # Extract snippets using RepoMap tags
            # Use budget_tokens parameter, with sensible defaults for snippet extraction
            # Cap at 5000 to avoid excessive memory usage
            snippet_budget = min(max(budget_tokens, 100), 5000)  # Clamp to [100, 5000]
            per_snippet_cap = max(snippet_budget // 5, 50)  # Minimum 50 tokens per snippet

            context_snippets = repomap.get_ranked_snippets(
                ranked_tags=ranked_tags,
                ranked_files=ranked[:20],  # Use top-20 from coarse ranking
                max_snippets_per_file=2,
                global_token_budget=snippet_budget,
                per_snippet_token_cap=per_snippet_cap,
                mentioned_idents=mentioned_idents  # Pass query terms for prioritization
            )

        except Exception as e:
            # Fallback: RepoMap failed, use coarse ranking only
            import sys
            print(f"Warning: RepoMap snippet extraction failed: {e}", file=sys.stderr)
            ranked = coarse_ranked
            context_snippets = []
    else:
        # Fallback: No RepoMap available, use GraphRanker only
        ranker = GraphRanker(root, verbose=False)
        ranked = ranker.rank_files(
            files=all_files,
            focus_files=focus_files or [],
            mentioned_files=mentioned_files
        )
        context_snippets = []

    # Build response with tier assignment
    ranked_files = []
    for f, r in ranked[:20]:
        # Assign tier based on rank
        if r > 0.5:
            tier = 1
        elif r > 0.2:
            tier = 2
        else:
            tier = 3

        ranked_files.append({
            "file": f,
            "rank": r,
            "tier": tier
        })

    return {
        "ranked_files": ranked_files,
        "explanation": f"Found {len(ranked)} files, showing top 20",
        "context_snippets": context_snippets,
    }
