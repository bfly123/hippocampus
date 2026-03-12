"""Graph ranking helpers for embedded RepoMap."""

from __future__ import annotations

import math
from collections import Counter, defaultdict

import networkx as nx

from .repomap_graph_support import (
    collect_graph_inputs,
    edge_weight,
    ensure_reference_map,
    ident_multiplier,
)


def _build_reference_graph(
    repomap,
    defines,
    references,
    *,
    mentioned_idents: set[str],
    chat_rel_fnames: set[str],
    progress=None,
):
    graph = nx.MultiDiGraph()

    for ident, definers in defines.items():
        if ident in references:
            continue
        for definer in definers:
            graph.add_edge(definer, definer, weight=0.1, ident=ident)

    for ident in set(defines.keys()).intersection(set(references.keys())):
        if progress:
            progress(f"{repomap.update_message}: {ident}")

        multiplier = ident_multiplier(ident, defines, mentioned_idents)
        for referencer, num_refs in Counter(references[ident]).items():
            for definer in defines[ident]:
                graph.add_edge(
                    referencer,
                    definer,
                    weight=edge_weight(
                        multiplier,
                        referencer,
                        chat_rel_fnames=chat_rel_fnames,
                        num_refs=num_refs,
                    ),
                    ident=ident,
                )

    return graph


def _pagerank(graph, personalization: dict[str, float]):
    pagerank_args = (
        {"personalization": personalization, "dangling": personalization}
        if personalization
        else {}
    )
    try:
        return nx.pagerank(graph, weight="weight", **pagerank_args)
    except ZeroDivisionError:
        try:
            return nx.pagerank(graph, weight="weight")
        except ZeroDivisionError:
            return {}


def _ranked_definitions(graph, ranked, *, progress, update_message: str):
    ranked_scores = defaultdict(float)
    for source in graph.nodes:
        if progress:
            progress(f"{update_message}: {source}")

        source_rank = ranked[source]
        total_weight = sum(data["weight"] for _src, _dst, data in graph.out_edges(source, data=True))
        for _src, dst, data in graph.out_edges(source, data=True):
            data["rank"] = source_rank * data["weight"] / total_weight
            ranked_scores[(dst, data["ident"])] += data["rank"]

    return sorted(ranked_scores.items(), reverse=True, key=lambda item: (item[1], item[0]))


def _append_ranked_tags(
    definitions,
    ranked_definitions,
    *,
    chat_rel_fnames: set[str],
) -> list[tuple]:
    ranked_tags: list[tuple] = []
    for (fname, ident), _rank in ranked_definitions:
        if fname in chat_rel_fnames:
            continue
        ranked_tags.extend(list(definitions.get((fname, ident), [])))
    return ranked_tags


def _append_fallback_files(repomap, ranked_tags, ranked, other_fnames):
    rel_other_without_tags = {repomap._get_rel_fname(fname) for fname in other_fnames}
    included_files = {tag[0] for tag in ranked_tags}
    ranked_nodes = sorted(((rank, node) for node, rank in ranked.items()), reverse=True)
    for _rank, fname in ranked_nodes:
        rel_other_without_tags.discard(fname)
        if fname not in included_files:
            ranked_tags.append((fname,))
    for fname in rel_other_without_tags:
        ranked_tags.append((fname,))
    return ranked_tags


def get_ranked_tags(
    repomap,
    chat_fnames,
    other_fnames,
    mentioned_fnames,
    mentioned_idents,
    progress=None,
):
    (
        defines,
        references,
        definitions,
        personalization,
        chat_rel_fnames,
    ) = collect_graph_inputs(
        repomap,
        chat_fnames,
        other_fnames,
        mentioned_fnames,
        mentioned_idents,
        progress=progress,
    )

    references = ensure_reference_map(defines, references)
    graph = _build_reference_graph(
        repomap,
        defines,
        references,
        mentioned_idents=mentioned_idents,
        chat_rel_fnames=chat_rel_fnames,
        progress=progress,
    )
    ranked = _pagerank(graph, personalization)
    if not ranked:
        return []

    ranked_definitions = _ranked_definitions(
        graph,
        ranked,
        progress=progress,
        update_message=repomap.update_message,
    )
    ranked_tags = _append_ranked_tags(
        definitions,
        ranked_definitions,
        chat_rel_fnames=chat_rel_fnames,
    )
    return _append_fallback_files(repomap, ranked_tags, ranked, other_fnames)
