"""Dynamic trimmer — trims repomix compress output by token budget."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Set

from ..utils import estimate_tokens, read_json, write_json


def _group_files_by_dir(files: dict[str, str]) -> dict[str, list[tuple[str, str]]]:
    """Group file paths by their parent directory."""
    groups: dict[str, list[tuple[str, str]]] = {}
    for fpath, content in files.items():
        parts = fpath.split("/")
        dir_key = parts[0] if len(parts) > 1 else "."
        groups.setdefault(dir_key, []).append((fpath, content))
    return groups


def _dir_line_count(files: list[tuple[str, str]]) -> int:
    """Count total lines in a directory's files."""
    return sum(content.count("\n") + 1 for _, content in files)


def trim_compress(
    compress_data: dict,
    budget: int,
) -> dict[str, str]:
    """Trim compress output to fit within token budget.

    Algorithm: sort directories by line count descending,
    expand files per directory until budget exhausted.

    NOTE: This is the legacy algorithm, kept for backward compatibility.
    Use trim_compress_with_ranker for better results.
    """
    files_data = compress_data.get("files", {})
    if not files_data:
        return {}

    # NOTE: No filtering here to maintain backward compatibility
    # Filtering is done in trim_compress_with_ranker instead

    groups = _group_files_by_dir(files_data)

    # Sort dirs by line count descending
    sorted_dirs = sorted(
        groups.items(),
        key=lambda kv: _dir_line_count(kv[1]),
        reverse=True,
    )

    result: dict[str, str] = {}
    remaining = budget

    for _dir_name, dir_files in sorted_dirs:
        if remaining <= 0:
            break
        for fpath, content in dir_files:
            cost = estimate_tokens(content)
            if cost > remaining:
                continue
            result[fpath] = content
            remaining -= cost

    return result


def trim_compress_with_ranker(
    compress_data: dict,
    budget: int,
    repo_root: Path,
    ranker,
    focus_files: List[str] = None,
    mentioned_files: Set[str] = None,
    verbose: bool = False,
) -> dict:
    """Trim using a FileRanker strategy."""
    files_data = compress_data.get("files", {})
    if not files_data:
        return {"files": {}, "metadata": {"error": "No files"}}

    # Filter empty files
    files_data = {
        fpath: content
        for fpath, content in files_data.items()
        if len(content.strip()) >= 10
    }

    # Use ranker to sort files
    ranked = ranker.rank_files(
        list(files_data.keys()),
        focus_files=focus_files,
        mentioned_files=mentioned_files,
    )

    # Select files by ranking order (greedy knapsack)
    # Use hybrid sorting to balance monotonicity and importance:
    # - Combine score (importance) and density (efficiency)
    # - Prevents tiny files from dominating selection
    # - Maintains reasonable overlap between budget levels
    result = {}
    remaining = budget
    selection_details = []

    # Prepare candidates with metadata
    candidates = []
    for fpath, score in ranked:
        content = files_data[fpath]
        cost = estimate_tokens(content)
        density = score / max(cost, 1)  # Value per token
        candidates.append((fpath, content, score, cost, density))

    # Hybrid sorting: 70% score + 30% density
    # This balances importance (score) with efficiency (density)
    # Prevents both large files blocking small files AND tiny files dominating
    def hybrid_key(item):
        _, _, score, cost, density = item
        # Normalize density to [0, 1] range with linear cap
        # (prevents extreme density values from dominating)
        normalized_density = min(density / 0.01, 1.0)  # Cap at 0.01 density
        return 0.7 * score + 0.3 * normalized_density

    candidates.sort(key=hybrid_key, reverse=True)

    # Greedy selection by hybrid order
    for fpath, content, score, cost, density in candidates:
        if cost <= remaining:
            result[fpath] = content
            remaining -= cost
            selection_details.append({
                "path": fpath,
                "score": round(score, 4),
                "cost": cost,
                "density": round(density, 6),
                "rank": len(selection_details) + 1,
            })

    return {
        "files": result,
        "metadata": {
            "selected_count": len(result),
            "total_tokens": budget - remaining,
            "remaining_budget": remaining,
            "ranking_method": ranker.__class__.__name__,
            "selection_details": selection_details,
        }
    }


def run_trimmer(
    target: Path,
    output_dir: Path,
    budget: int = 10000,
    compress_data: dict | None = None,
    ranking_method: str = "graph",  # "heuristic", "graph", or "symbol"
    focus_files: List[str] = None,
    mentioned_files: Set[str] = None,
    verbose: bool = False,
) -> dict[str, str]:
    """Run the trimmer on repomix compress output.

    If compress_data is not provided, runs repomix compress first.
    """
    from .ranker import HeuristicRanker, GraphRanker, is_repomap_available

    if compress_data is None:
        from ..repomix.runner import run_repomix_compress
        import tempfile
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
        try:
            compress_data = run_repomix_compress(target, tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    # Select ranker with graceful degradation
    if ranking_method == "symbol":
        if not is_repomap_available(target):
            import sys
            print("Warning: SymbolRanker dependencies not available, falling back to GraphRanker", file=sys.stderr)
            print("  Install with: pip install -e '.[repomap]'", file=sys.stderr)
            ranker = GraphRanker(target, verbose=verbose)
        else:
            try:
                from .ranker import SymbolRanker
                ranker = SymbolRanker(target, verbose=verbose)
            except ImportError as e:
                import sys
                print(f"Warning: Failed to load SymbolRanker ({e}), falling back to GraphRanker", file=sys.stderr)
                ranker = GraphRanker(target, verbose=verbose)
    elif ranking_method == "graph":
        ranker = GraphRanker(target, verbose=verbose)
    else:
        ranker = HeuristicRanker()

    # Execute trimming
    trimmed_data = trim_compress_with_ranker(
        compress_data,
        budget,
        repo_root=target,
        ranker=ranker,
        focus_files=focus_files,
        mentioned_files=mentioned_files,
        verbose=verbose,
    )

    # Write output
    from ..constants import TRIMMED_FILE
    out_path = output_dir / TRIMMED_FILE
    write_json(out_path, {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "budget": budget,
        "file_count": len(trimmed_data["files"]),
        "files": trimmed_data["files"],
        **trimmed_data["metadata"],
    })

    return trimmed_data["files"]
