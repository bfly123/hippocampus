"""Graph-based file ranking strategy."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set, Tuple

import networkx as nx

from .ranker_common import FileRanker
from .ranker_heuristic import HeuristicRanker


class GraphRanker(FileRanker):
    """Graph-based ranker inspired by Aider's PageRank approach."""

    def __init__(self, root: Path, verbose: bool = False):
        self.root = root
        self.verbose = verbose

    def rank_files(
        self,
        files: List[str],
        focus_files: List[str] = None,
        mentioned_files: Set[str] = None,
    ) -> List[Tuple[str, float]]:
        """Rank files using dependency graph and PageRank."""
        focus_set = set(focus_files or [])
        mentioned_set = mentioned_files or set()

        graph = self._build_dependency_graph(files)

        num_edges = graph.number_of_edges()
        num_nodes = graph.number_of_nodes()
        edge_density = num_edges / max(num_nodes, 1)

        if self.verbose:
            print(
                f"Graph: {num_nodes} nodes, {num_edges} edges, density={edge_density:.3f}"
            )

        if edge_density < 0.05:
            if self.verbose:
                print("Graph too sparse, falling back to heuristic")
            return HeuristicRanker().rank_files(files, focus_files, mentioned_files)

        personalization = self._compute_personalization(files, focus_set, mentioned_set)

        try:
            if personalization:
                ranked = nx.pagerank(
                    graph,
                    weight="weight",
                    personalization=personalization,
                    max_iter=100,
                )
            else:
                ranked = nx.pagerank(graph, weight="weight", max_iter=100)
        except (
            ZeroDivisionError,
            nx.PowerIterationFailedConvergence,
            ImportError,
            ModuleNotFoundError,
            AttributeError,
        ) as exc:
            if self.verbose:
                print(
                    f"PageRank failed ({type(exc).__name__}), falling back to heuristic"
                )
            return HeuristicRanker().rank_files(files, focus_files, mentioned_files)

        heuristic_ranker = HeuristicRanker()
        heuristic_scores = dict(
            heuristic_ranker.rank_files(files, focus_files, mentioned_files)
        )

        max_pr = max(ranked.values()) if ranked else 1.0
        max_heur = max(heuristic_scores.values()) if heuristic_scores else 1.0

        blended = []
        for fpath in files:
            pr_score = ranked.get(fpath, 0.0) / max_pr
            heur_score = heuristic_scores.get(fpath, 0.0) / max_heur
            final_score = 0.4 * pr_score + 0.6 * heur_score
            blended.append((fpath, final_score))

        blended.sort(key=lambda x: (-x[1], x[0]))
        return blended

    def _build_dependency_graph(self, files: List[str]) -> nx.MultiDiGraph:
        """Build file dependency graph based on import statements."""
        graph = nx.MultiDiGraph()

        for fpath in files:
            graph.add_node(fpath)

        for fpath in files:
            try:
                full_path = self.root / fpath
                if not full_path.exists():
                    continue
                content = full_path.read_text(encoding="utf-8", errors="ignore")
                imports = self._extract_imports(content, fpath)

                for imported_file in imports:
                    if imported_file in files:
                        graph.add_edge(fpath, imported_file, weight=1.0)
            except (OSError, UnicodeDecodeError) as exc:
                if self.verbose:
                    print(f"Warning: Could not read {fpath}: {exc}")
                continue
            except Exception as exc:
                if self.verbose:
                    print(
                        f"Warning: Unexpected error processing {fpath}: {type(exc).__name__}"
                    )
                continue

        return graph

    def _extract_imports(self, content: str, fpath: str) -> List[str]:
        """Extract import statements and convert to file paths."""
        imports = []
        lines = content.split("\n")

        fpath_parts = fpath.split("/")
        if len(fpath_parts) > 1:
            current_dir = "/".join(fpath_parts[:-1])
        else:
            current_dir = ""

        for raw_line in lines:
            line = raw_line.strip()
            if not (line.startswith("import ") or line.startswith("from ")):
                continue

            if line.startswith("from "):
                parts = line.split()
                if len(parts) < 2:
                    continue
                module_path = parts[1]

                if module_path.startswith("."):
                    dots = len(module_path) - len(module_path.lstrip("."))
                    module_path = module_path.lstrip(".")

                    if current_dir:
                        dir_parts = current_dir.split("/")
                        if dots > 1:
                            dir_parts = dir_parts[: -(dots - 1)]
                        base_dir = "/".join(dir_parts)
                    else:
                        base_dir = ""

                    if module_path:
                        file_path = module_path.replace(".", "/")
                        if base_dir:
                            full_path = f"{base_dir}/{file_path}.py"
                        else:
                            full_path = f"{file_path}.py"
                        imports.append(full_path)
                        if base_dir:
                            imports.append(f"{base_dir}/{file_path}/__init__.py")
                        else:
                            imports.append(f"{file_path}/__init__.py")
                else:
                    file_path = module_path.replace(".", "/")
                    imports.append(f"src/{file_path}.py")
                    imports.append(f"{file_path}.py")
                    imports.append(f"src/{file_path}/__init__.py")

            elif line.startswith("import "):
                parts = line.split()
                if len(parts) < 2:
                    continue
                module_path = parts[1].split(",")[0].strip()

                file_path = module_path.replace(".", "/")
                imports.append(f"src/{file_path}.py")
                imports.append(f"{file_path}.py")

        return imports

    def _compute_personalization(
        self,
        files: List[str],
        focus_set: Set[str],
        mentioned_set: Set[str],
    ) -> Dict[str, float]:
        """Compute personalization vector for PageRank."""
        if not focus_set and not mentioned_set:
            return {}

        personalization = {}
        base_score = 100.0 / len(files)

        for fpath in files:
            score = 0.0

            if fpath in focus_set:
                score += base_score * 5.0

            if fpath in mentioned_set:
                score += base_score

            if score > 0:
                personalization[fpath] = score

        return personalization


__all__ = ["GraphRanker"]
