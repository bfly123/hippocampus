"""
Context generation with tiered token budget allocation.

Renders navigation context with focus/related/context file sections.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple


def allocate_token_budget(max_tokens: int) -> Dict[int, int]:
    """
    Allocate token budget across tiers.

    Tier 1: 50% (focus files)
    Tier 2: 40% (related files)
    Tier 3: 10% (context files)

    Args:
        max_tokens: Total token budget

    Returns:
        Dict of {tier: budget}
    """
    return {
        1: int(max_tokens * 0.5),
        2: int(max_tokens * 0.4),
        3: int(max_tokens * 0.1)
    }


def _estimate_file_tokens(file_path: Path) -> int:
    """Estimate token count for a file (rough: chars / 4)."""
    try:
        content = file_path.read_text()
        return len(content) // 4
    except Exception:
        return 0


def _truncate_content(content: str, max_tokens: int) -> str:
    """Truncate content to fit within token budget."""
    max_chars = max_tokens * 4
    if len(content) <= max_chars:
        return content

    # Truncate and add marker
    lines = content.split('\n')
    truncated = []
    char_count = 0

    for line in lines:
        if char_count + len(line) + 1 > max_chars:
            truncated.append(f"... (truncated, {len(lines) - len(truncated)} lines omitted)")
            break
        truncated.append(line)
        char_count += len(line) + 1

    return '\n'.join(truncated)


def select_files_by_tier(
    ranked_files: Dict[str, Tuple[float, int]],
    tier_budgets: Dict[int, int],
    root: Path
) -> List[str]:
    """
    Select files by tier within token budgets.

    Args:
        ranked_files: Dict of {file: (rank, tier)}
        tier_budgets: Dict of {tier: token_budget}
        root: Repository root

    Returns:
        List of selected file paths
    """
    selected = []

    for tier in [1, 2, 3]:
        tier_files = [
            (f, r) for f, (r, t) in ranked_files.items()
            if t == tier
        ]
        tier_files.sort(key=lambda x: x[1], reverse=True)

        budget = tier_budgets.get(tier, 0)
        used = 0

        for file, _ in tier_files:
            file_path = root / file
            tokens = _estimate_file_tokens(file_path)

            if used + tokens <= budget:
                selected.append(file)
                used += tokens
            # Removed: forced inclusion of at least one file per tier
            # This was causing budget overruns

    return selected


def render_context(
    ranked_files: Dict[str, Tuple[float, int]],
    selected_files: List[str],
    root: Path,
    max_tokens_per_file: int = 500
) -> str:
    """
    Render navigation context as markdown.

    Args:
        ranked_files: Dict of {file: (rank, tier)}
        selected_files: List of selected files
        root: Repository root
        max_tokens_per_file: Max tokens per file (default 500)

    Returns:
        Markdown formatted context
    """
    output = ["# Task Context (Navigation Plane)\n"]

    tier_names = {
        1: "Focus Files",
        2: "Related Files",
        3: "Context Files"
    }

    for tier in [1, 2, 3]:
        tier_files = [
            f for f in selected_files
            if ranked_files[f][1] == tier
        ]

        if not tier_files:
            continue

        output.append(f"\n## {tier_names[tier]} (Tier {tier})\n")

        for file in tier_files:
            rank, _ = ranked_files[file]
            output.append(f"\n### {file} (rank: {rank:.3f})\n")

            # Read and truncate file content
            file_path = root / file
            try:
                content = file_path.read_text()
                truncated = _truncate_content(content, max_tokens_per_file)
                output.append(f"```\n{truncated}\n```\n")
            except Exception as e:
                output.append(f"*Error reading file: {e}*\n")

    return "".join(output)
