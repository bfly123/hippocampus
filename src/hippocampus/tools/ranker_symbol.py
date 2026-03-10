"""Symbol-level file ranking strategy."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

from .ranker_common import FileRanker
from .ranker_heuristic import HeuristicRanker
from .repomap_adapter import check_repomap_available


class SymbolRanker(FileRanker):
    """Symbol-level ranker using Aider RepoMap (experimental)."""

    def __init__(self, root: Path, verbose: bool = False):
        self.root = root
        self.verbose = verbose

        available, error = check_repomap_available(root)
        if not available:
            raise ImportError(
                "SymbolRanker requires optional dependencies. "
                "Install with: pip install -e '.[repomap]'\n"
                f"Error: {error}"
            )

        from .repomap_adapter import HippoRepoMap

        self.repomap = HippoRepoMap(root=root, map_tokens=2048, verbose=verbose)
        self.heuristic_ranker = HeuristicRanker()

    def rank_files(
        self,
        files: List[str],
        focus_files: List[str] = None,
        mentioned_files: Set[str] = None,
    ) -> List[Tuple[str, float]]:
        """Rank files using symbol-level analysis with hybrid strategy."""
        focus_files = focus_files or []
        mentioned_files = mentioned_files or set()

        try:
            ranked_tags = self.repomap.get_ranked_tags(
                chat_files=focus_files if focus_files else files[:1],
                other_files=[f for f in files if f not in focus_files],
                mentioned_files=mentioned_files,
                mentioned_idents=set(),
            )

            file_symbol_scores = self._aggregate_symbol_scores(ranked_tags)

            heuristic_scores = dict(
                self.heuristic_ranker.rank_files(files, focus_files, mentioned_files)
            )

            max_symbol = max(file_symbol_scores.values()) if file_symbol_scores else 1.0
            max_heur = max(heuristic_scores.values()) if heuristic_scores else 1.0

            blended = []
            for fpath in files:
                symbol_score = file_symbol_scores.get(fpath, 0.0) / max_symbol
                heur_score = heuristic_scores.get(fpath, 0.0) / max_heur
                final_score = 0.6 * symbol_score + 0.4 * heur_score
                blended.append((fpath, final_score))

            blended.sort(key=lambda x: (-x[1], x[0]))
            return blended

        except Exception as exc:
            if self.verbose:
                print(f"SymbolRanker error, falling back to heuristic: {exc}")
            return self.heuristic_ranker.rank_files(files, focus_files, mentioned_files)

    def _aggregate_symbol_scores(
        self,
        ranked_tags: List[Tuple[str, str, int, str, str]],
    ) -> Dict[str, float]:
        """Aggregate symbol-level scores to file-level scores."""
        file_scores = defaultdict(float)

        for rank, tag in enumerate(ranked_tags):
            rel_fname = tag[0]
            score = 0.95 ** rank
            file_scores[rel_fname] += score

        return dict(file_scores)


__all__ = ["SymbolRanker"]
