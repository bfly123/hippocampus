"""
Graph-based file ranking using PageRank.

Builds dependency graph from code references and ranks files
by task relevance using personalized PageRank.
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


def _compute_edge_weight(
    ident: str,
    ref_file: str,
    def_files: List[str],
    ref_count: int,
    mentioned_idents: Set[str],
    chat_files: Set[str]
) -> float:
    """
    Compute edge weight based on aider's mul factors.

    Args:
        ident: Identifier name
        ref_file: File containing the reference
        def_files: Files containing definitions
        ref_count: Number of references from ref_file
        mentioned_idents: Identifiers mentioned in conversation
        chat_files: Files in active conversation

    Returns:
        Edge weight
    """
    mul = 1.0

    # Mentioned identifier: ×10
    if ident in mentioned_idents:
        mul *= 10

    # Well-named identifier (length ≥ 8, not starting with _): ×10
    if len(ident) >= 8 and not ident.startswith("_"):
        mul *= 10

    # Private identifier (starts with _): ×0.1
    if ident.startswith("_"):
        mul *= 0.1

    # Too many definitions (> 5): ×0.1
    if len(def_files) > 5:
        mul *= 0.1

    # Reference from chat file: ×50
    if ref_file in chat_files:
        mul *= 50

    # Weight = mul × sqrt(ref_count)
    return mul * (ref_count ** 0.5)


def _build_dependency_graph(
    all_files: Set[str],
    defines: Dict[str, List[str]],
    references: Dict[str, List[Tuple[str, int]]],
    mentioned_idents: Set[str],
    chat_files: Set[str]
) -> "nx.MultiDiGraph":
    """
    Build dependency graph from definitions and references.

    Args:
        all_files: All tracked files
        defines: Map of ident -> [defining files]
        references: Map of ident -> [(ref_file, line), ...]
        mentioned_idents: Identifiers mentioned in conversation
        chat_files: Files in active conversation

    Returns:
        NetworkX MultiDiGraph
    """
    if not HAS_NETWORKX:
        raise ImportError("networkx is required for graph ranking")

    G = nx.MultiDiGraph()
    G.add_nodes_from(all_files)

    # Pre-compute reference counts per file to avoid O(n²)
    from collections import Counter

    for ident, ref_list in references.items():
        if ident not in defines:
            continue

        def_files = defines[ident]
        # Count references per file once
        ref_counts = Counter(r[0] for r in ref_list)

        for ref_file, count in ref_counts.items():
            for def_file in def_files:
                if ref_file != def_file:
                    weight = _compute_edge_weight(
                        ident, ref_file, def_files, count,
                        mentioned_idents, chat_files
                    )
                    G.add_edge(ref_file, def_file, weight=weight)

    return G


def rank_files_tiered(
    all_files: Set[str],
    defines: Dict[str, List[str]],
    references: Dict[str, List[Tuple[str, int]]],
    chat_files: Set[str],
    mentioned_idents: Set[str],
    mentioned_files: Set[str],
    global_priors: Dict[str, float] = None,
) -> Dict[str, Tuple[float, int]]:
    """
    Rank files using tiered PageRank strategy.

    Tier 1: Focus files (conversation mentions)
    Tier 2: Related files (dependency path)
    Tier 3: Context files (global importance)

    Args:
        all_files: All tracked files
        defines: Map of ident -> [defining files]
        references: Map of ident -> [(ref_file, line), ...]
        chat_files: Files in active conversation
        mentioned_idents: Identifiers mentioned
        mentioned_files: Files explicitly mentioned
        global_priors: Optional global importance scores

    Returns:
        Dict of {file: (rank, tier)}
    """
    if not HAS_NETWORKX:
        raise ImportError("networkx is required for graph ranking")

    # 1. Build dependency graph
    G = _build_dependency_graph(
        all_files, defines, references,
        mentioned_idents, chat_files
    )

    # 2. Tier 1: Focus files (highest priority)
    tier1_files = chat_files | mentioned_files
    tier1_ranked = {f: 1.0 for f in tier1_files}

    # 3. Tier 2: Task-relevant files (dependency path)
    personalization = {
        f: (100.0 if f in tier1_files else 0.0)
        for f in all_files
    }
    total = sum(personalization.values())
    if total > 0:
        personalization = {f: w / total for f, w in personalization.items()}

    if G.number_of_edges() > 0:
        task_ranked = nx.pagerank(G, weight="weight", personalization=personalization)
    else:
        task_ranked = personalization

    # Filter Tier 2 (exclude Tier 1)
    tier2_ranked = {
        f: r for f, r in task_ranked.items()
        if f not in tier1_files and r > 0.001
    }

    # 4. Tier 3: Global context files
    tier3_ranked = {}
    if global_priors:
        tier3_ranked = {
            f: global_priors.get(f, 0.0)
            for f in all_files
            if f not in tier1_files and f not in tier2_ranked
        }

    # 5. Merge results with tier labels
    result = {}
    for f, r in tier1_ranked.items():
        result[f] = (r, 1)
    for f, r in sorted(tier2_ranked.items(), key=lambda x: x[1], reverse=True):
        result[f] = (r, 2)
    for f, r in sorted(tier3_ranked.items(), key=lambda x: x[1], reverse=True):
        result[f] = (r, 3)

    return result
