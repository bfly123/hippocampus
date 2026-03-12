"""Heuristic file ranking strategy."""

from __future__ import annotations

from typing import List, Set, Tuple

from .ranker_common import FileRanker


class HeuristicRanker(FileRanker):
    """Simple heuristic-based ranker."""

    def rank_files(
        self,
        files: List[str],
        focus_files: List[str] = None,
        mentioned_files: Set[str] = None,
    ) -> List[Tuple[str, float]]:
        """Rank files using heuristic rules."""
        focus_set = set(focus_files or [])
        mentioned_set = mentioned_files or set()

        scored = []
        for fpath in files:
            score = self._compute_score(fpath, focus_set, mentioned_set)
            scored.append((fpath, score))

        scored.sort(key=lambda x: (-x[1], x[0]))
        return scored

    def _compute_score(
        self,
        fpath: str,
        focus_set: Set[str],
        mentioned_set: Set[str],
    ) -> float:
        score = 1.0

        if fpath in focus_set:
            score *= 50.0

        if fpath in mentioned_set:
            score *= 10.0

        if fpath.endswith(".md") or fpath.endswith(".txt"):
            score *= 0.3
        elif fpath.startswith("src/") or fpath.startswith("lib/"):
            score *= 2.0

        if "/tools/" in fpath or fpath.startswith("tools/"):
            score *= 2.5

        if fpath.endswith("__init__.py"):
            score *= 0.5
        elif fpath.endswith(".py") and "test" not in fpath.lower():
            score *= 1.5

        core_patterns = [
            "cli.py",
            "main.py",
            "processor.py",
            "engine.py",
            "core.py",
            "trimmer.py",
            "runner.py",
            "indexer.py",
            "parser.py",
        ]
        if any(pattern in fpath for pattern in core_patterns):
            score *= 3.0

        if "test" in fpath.lower() or "spec" in fpath.lower():
            score *= 0.2
        if fpath.startswith("plans/") or fpath.startswith("docs/"):
            score *= 0.4

        return score


__all__ = ["HeuristicRanker"]
