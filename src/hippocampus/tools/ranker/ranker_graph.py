"""Graph-based file ranking strategy."""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from .ranker_common import FileRanker
from .ranker_graph_parsing import extract_imports
from .ranker_heuristic import HeuristicRanker


def _warn(verbose: bool, message: str) -> None:
    if verbose:
        print(message)


class GraphRanker(FileRanker):
    """Graph-based ranker inspired by Aider's PageRank approach."""

    def __init__(self, root: Path, verbose: bool = False):
        self.root = root
        self.verbose = verbose

    def rank_files(
        self,
        files: list[str],
        focus_files: list[str] | None = None,
        mentioned_files: set[str] | None = None,
    ) -> list[tuple[str, float]]:
        """Rank files using dependency graph and PageRank."""
        graph = self._build_dependency_graph(files)
        if self._should_fallback(graph):
            return HeuristicRanker().rank_files(files, focus_files, mentioned_files)

        ranked = self._run_pagerank(
            graph,
            files,
            focus_set=set(focus_files or []),
            mentioned_set=mentioned_files or set(),
        )
        if ranked is None:
            return HeuristicRanker().rank_files(files, focus_files, mentioned_files)
        return self._blend_scores(files, ranked, focus_files, mentioned_files)

    def _should_fallback(self, graph: nx.MultiDiGraph) -> bool:
        num_edges = graph.number_of_edges()
        num_nodes = graph.number_of_nodes()
        edge_density = num_edges / max(num_nodes, 1)
        _warn(
            self.verbose,
            f"Graph: {num_nodes} nodes, {num_edges} edges, density={edge_density:.3f}",
        )
        if edge_density < 0.05:
            _warn(self.verbose, "Graph too sparse, falling back to heuristic")
            return True
        return False

    def _run_pagerank(
        self,
        graph: nx.MultiDiGraph,
        files: list[str],
        *,
        focus_set: set[str],
        mentioned_set: set[str],
    ) -> dict[str, float] | None:
        personalization = self._compute_personalization(files, focus_set, mentioned_set)
        try:
            if personalization:
                return nx.pagerank(
                    graph,
                    weight="weight",
                    personalization=personalization,
                    max_iter=100,
                )
            return nx.pagerank(graph, weight="weight", max_iter=100)
        except (
            ZeroDivisionError,
            nx.PowerIterationFailedConvergence,
            ImportError,
            ModuleNotFoundError,
            AttributeError,
        ) as exc:
            _warn(
                self.verbose,
                f"PageRank failed ({type(exc).__name__}), falling back to heuristic",
            )
            return None

    def _blend_scores(
        self,
        files: list[str],
        ranked: dict[str, float],
        focus_files: list[str] | None,
        mentioned_files: set[str] | None,
    ) -> list[tuple[str, float]]:
        heuristic_scores = dict(
            HeuristicRanker().rank_files(files, focus_files, mentioned_files)
        )
        max_pr = max(ranked.values()) if ranked else 1.0
        max_heur = max(heuristic_scores.values()) if heuristic_scores else 1.0

        blended = []
        for file_path in files:
            pr_score = ranked.get(file_path, 0.0) / max_pr
            heur_score = heuristic_scores.get(file_path, 0.0) / max_heur
            blended.append((file_path, 0.4 * pr_score + 0.6 * heur_score))
        blended.sort(key=lambda item: (-item[1], item[0]))
        return blended

    def _build_dependency_graph(self, files: list[str]) -> nx.MultiDiGraph:
        """Build file dependency graph based on import statements."""
        graph = nx.MultiDiGraph()
        graph.add_nodes_from(files)
        for file_path in files:
            self._add_dependency_edges(graph, file_path, files)
        return graph

    def _add_dependency_edges(
        self,
        graph: nx.MultiDiGraph,
        file_path: str,
        files: list[str],
    ) -> None:
        try:
            imports = self._read_imports(file_path)
            for imported_file in imports:
                if imported_file in files:
                    graph.add_edge(file_path, imported_file, weight=1.0)
        except (OSError, UnicodeDecodeError) as exc:
            _warn(self.verbose, f"Warning: Could not read {file_path}: {exc}")
        except Exception as exc:
            _warn(
                self.verbose,
                "Warning: Unexpected error processing "
                f"{file_path}: {type(exc).__name__}",
            )

    def _read_imports(self, file_path: str) -> list[str]:
        full_path = self.root / file_path
        if not full_path.exists():
            return []
        content = full_path.read_text(encoding="utf-8", errors="ignore")
        return extract_imports(content, file_path)

    def _compute_personalization(
        self,
        files: list[str],
        focus_set: set[str],
        mentioned_set: set[str],
    ) -> dict[str, float]:
        """Compute personalization vector for PageRank."""
        if not focus_set and not mentioned_set:
            return {}

        personalization = {}
        base_score = 100.0 / len(files)
        for file_path in files:
            score = 0.0
            if file_path in focus_set:
                score += base_score * 5.0
            if file_path in mentioned_set:
                score += base_score
            if score > 0:
                personalization[file_path] = score
        return personalization


__all__ = ["GraphRanker"]
