"""Support helpers for trim selection and ranker loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..utils import estimate_tokens

Candidate = tuple[str, str, float, int, float]


def filter_meaningful_files(files_data: dict[str, str]) -> dict[str, str]:
    return {
        file_path: content
        for file_path, content in files_data.items()
        if len(content.strip()) >= 10
    }


def build_candidates(
    ranked: list[tuple[str, float]],
    files_data: dict[str, str],
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for file_path, score in ranked:
        content = files_data[file_path]
        cost = estimate_tokens(content)
        density = score / max(cost, 1)
        candidates.append((file_path, content, score, cost, density))
    candidates.sort(key=_hybrid_candidate_key, reverse=True)
    return candidates


def _hybrid_candidate_key(candidate: Candidate) -> float:
    _, _, score, _cost, density = candidate
    normalized_density = min(density / 0.01, 1.0)
    return 0.7 * score + 0.3 * normalized_density


def select_ranked_files(
    candidates: list[Candidate],
    *,
    budget: int,
) -> tuple[dict[str, str], int, list[dict[str, Any]]]:
    result: dict[str, str] = {}
    remaining = budget
    selection_details: list[dict[str, Any]] = []
    for file_path, content, score, cost, density in candidates:
        if cost > remaining:
            continue
        result[file_path] = content
        remaining -= cost
        selection_details.append(
            {
                "path": file_path,
                "score": round(score, 4),
                "cost": cost,
                "density": round(density, 6),
                "rank": len(selection_details) + 1,
            }
        )
    return result, remaining, selection_details


def load_compress_data(target: Path):
    from ..repomix.runner import run_repomix_compress
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        return run_repomix_compress(target, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def build_ranker(target: Path, ranking_method: str, *, verbose: bool):
    from .ranker import HeuristicRanker, GraphRanker, is_repomap_available

    if ranking_method == "symbol":
        return _build_symbol_ranker(
            target,
            verbose=verbose,
            graph_ranker_cls=GraphRanker,
            is_repomap_available_fn=is_repomap_available,
        )
    if ranking_method == "graph":
        return GraphRanker(target, verbose=verbose)
    return HeuristicRanker()


def _build_symbol_ranker(
    target: Path,
    *,
    verbose: bool,
    graph_ranker_cls,
    is_repomap_available_fn,
):
    import sys

    if not is_repomap_available_fn(target):
        print(
            "Warning: SymbolRanker dependencies not available, "
            "falling back to GraphRanker",
            file=sys.stderr,
        )
        print("  Install with: pip install -e '.[repomap]'", file=sys.stderr)
        return graph_ranker_cls(target, verbose=verbose)

    try:
        from .ranker import SymbolRanker

        return SymbolRanker(target, verbose=verbose)
    except ImportError as exc:
        print(
            f"Warning: Failed to load SymbolRanker ({exc}), "
            "falling back to GraphRanker",
            file=sys.stderr,
        )
        return graph_ranker_cls(target, verbose=verbose)
