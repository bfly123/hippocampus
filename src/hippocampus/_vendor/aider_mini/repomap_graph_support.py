"""Support helpers for RepoMap graph ranking."""

from __future__ import annotations

import math
import os
from collections import defaultdict
from pathlib import Path


def tags_cache_size(repomap, sqlite_errors) -> int:
    try:
        return len(repomap.TAGS_CACHE)
    except sqlite_errors as err:
        repomap._tags_cache_error(err)
        return len(repomap.TAGS_CACHE)


def prepare_file_iteration(repomap, fnames: list[str]):
    cache_size = tags_cache_size(repomap, repomap.sqlite_errors)
    if len(fnames) - cache_size > 100:
        repomap.io.tool_output(
            "Initial repo scan can be slow in larger repos, but only happens once."
        )
        return repomap.progress_bar(fnames, desc="Scanning repo"), True
    return fnames, False


def path_match_bonus(rel_fname: str, mentioned_idents: set[str], personalize: float) -> float:
    path_obj = Path(rel_fname)
    basename_with_ext = path_obj.name
    basename_without_ext, _ = os.path.splitext(basename_with_ext)
    components_to_check = set(path_obj.parts).union({basename_with_ext, basename_without_ext})
    return personalize if components_to_check.intersection(mentioned_idents) else 0.0


def personalization_score(
    fname: str,
    rel_fname: str,
    *,
    chat_fnames: set[str],
    mentioned_fnames: set[str],
    mentioned_idents: set[str],
    personalize: float,
) -> float:
    score = 0.0
    if fname in chat_fnames:
        score += personalize
    if rel_fname in mentioned_fnames:
        score = max(score, personalize)
    return score + path_match_bonus(rel_fname, mentioned_idents, personalize)


def iter_existing_files(repomap, fnames, *, progress, showing_bar):
    for fname in fnames:
        if repomap.verbose:
            repomap.io.tool_output(f"Processing {fname}")
        if progress and not showing_bar:
            progress(f"{repomap.update_message}: {fname}")

        try:
            file_ok = Path(fname).is_file()
        except OSError:
            file_ok = False

        if file_ok:
            yield fname
            continue

        if fname not in repomap.warned_files:
            repomap.io.tool_warning(f"Repo-map can't include {fname}")
            repomap.io.tool_output("Has it been deleted from the file system but not from git?")
            repomap.warned_files.add(fname)


def collect_graph_inputs(
    repomap,
    chat_fnames,
    other_fnames,
    mentioned_fnames,
    mentioned_idents,
    progress=None,
):
    defines = defaultdict(set)
    references = defaultdict(list)
    definitions = defaultdict(set)
    personalization: dict[str, float] = {}
    chat_rel_fnames: set[str] = set()

    fnames = sorted(set(chat_fnames).union(set(other_fnames)))
    personalize = 100 / len(fnames)
    iterable, showing_bar = prepare_file_iteration(repomap, fnames)
    chat_fnames_set = set(chat_fnames)

    for fname in iter_existing_files(
        repomap,
        iterable,
        progress=progress,
        showing_bar=showing_bar,
    ):
        rel_fname = repomap._get_rel_fname(fname)
        current_pers = personalization_score(
            fname,
            rel_fname,
            chat_fnames=chat_fnames_set,
            mentioned_fnames=mentioned_fnames,
            mentioned_idents=mentioned_idents,
            personalize=personalize,
        )
        if fname in chat_fnames_set:
            chat_rel_fnames.add(rel_fname)
        if current_pers > 0:
            personalization[rel_fname] = current_pers

        for tag in repomap.get_tags(fname, rel_fname):
            if tag.kind == "def":
                defines[tag.name].add(rel_fname)
                definitions[(rel_fname, tag.name)].add(tag)
            elif tag.kind == "ref":
                references[tag.name].append(rel_fname)

    return defines, references, definitions, personalization, chat_rel_fnames


def ensure_reference_map(defines, references):
    if references:
        return references
    return {ident: list(files) for ident, files in defines.items()}


def _ident_shape_multiplier(ident: str) -> float:
    is_snake = ("_" in ident) and any(char.isalpha() for char in ident)
    is_kebab = ("-" in ident) and any(char.isalpha() for char in ident)
    is_camel = any(char.isupper() for char in ident) and any(char.islower() for char in ident)
    return 10.0 if (is_snake or is_kebab or is_camel) and len(ident) >= 8 else 1.0


def ident_multiplier(ident: str, defines, mentioned_idents: set[str]) -> float:
    multiplier = 1.0
    for factor in (
        10.0 if ident in mentioned_idents else 1.0,
        _ident_shape_multiplier(ident),
        0.1 if ident.startswith("_") else 1.0,
        0.1 if len(defines[ident]) > 5 else 1.0,
    ):
        multiplier *= factor
    return multiplier


def edge_weight(multiplier: float, referencer: str, *, chat_rel_fnames: set[str], num_refs: int) -> float:
    if referencer in chat_rel_fnames:
        multiplier *= 50
    return multiplier * math.sqrt(num_refs)
