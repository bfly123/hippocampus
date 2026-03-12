"""Map-building helpers for embedded RepoMap."""

from __future__ import annotations

import time

from .special import filter_important_files
from .waiting import Spinner


def _cache_key(repomap, chat_fnames, other_fnames, max_map_tokens, mentioned_fnames, mentioned_idents):
    key = [
        tuple(sorted(chat_fnames)) if chat_fnames else None,
        tuple(sorted(other_fnames)) if other_fnames else None,
        max_map_tokens,
    ]
    if repomap.refresh == "auto":
        key.extend(
            [
                tuple(sorted(mentioned_fnames)) if mentioned_fnames else None,
                tuple(sorted(mentioned_idents)) if mentioned_idents else None,
            ]
        )
    return tuple(key)


def _use_cached_map(repomap, *, force_refresh: bool, cache_key):
    if force_refresh:
        return None
    if repomap.refresh == "manual" and repomap.last_map:
        return repomap.last_map
    if repomap.refresh == "always":
        return None

    use_cache = repomap.refresh == "files" or (
        repomap.refresh == "auto" and repomap.map_processing_time > 1.0
    )
    if use_cache and cache_key in repomap.map_cache:
        return repomap.map_cache[cache_key]
    return None


def get_ranked_tags_map(
    repomap,
    chat_fnames,
    other_fnames=None,
    max_map_tokens=None,
    mentioned_fnames=None,
    mentioned_idents=None,
    force_refresh=False,
):
    cache_key = _cache_key(
        repomap,
        chat_fnames,
        other_fnames,
        max_map_tokens,
        mentioned_fnames,
        mentioned_idents,
    )
    cached = _use_cached_map(repomap, force_refresh=force_refresh, cache_key=cache_key)
    if cached is not None:
        return cached

    start_time = time.time()
    result = get_ranked_tags_map_uncached(
        repomap,
        chat_fnames,
        other_fnames,
        max_map_tokens,
        mentioned_fnames,
        mentioned_idents,
    )
    repomap.map_processing_time = time.time() - start_time
    repomap.map_cache[cache_key] = result
    repomap.last_map = result
    return result


def _normalized_rank_inputs(repomap, other_fnames, max_map_tokens, mentioned_fnames, mentioned_idents):
    return (
        list(other_fnames or []),
        max_map_tokens or repomap.max_map_tokens,
        set(mentioned_fnames or set()),
        set(mentioned_idents or set()),
    )


def _prepend_special_fnames(repomap, ranked_tags, other_fnames):
    other_rel_fnames = sorted({repomap._get_rel_fname(fname) for fname in other_fnames})
    special_fnames = filter_important_files(other_rel_fnames)
    ranked_tags_fnames = {tag[0] for tag in ranked_tags}
    missing_specials = [(fname,) for fname in special_fnames if fname not in ranked_tags_fnames]
    return missing_specials + ranked_tags


def _find_best_tree(repomap, ranked_tags, chat_rel_fnames, max_map_tokens, spinner):
    num_tags = len(ranked_tags)
    lower_bound = 0
    upper_bound = num_tags
    best_tree = None
    best_tree_tokens = 0
    middle = min(int(max_map_tokens // 25), num_tags)

    while lower_bound <= upper_bound:
        display = f"{middle / 1000.0:.1f}K" if middle > 1500 else str(middle)
        spinner.step(f"{repomap.update_message}: {display} tokens")

        tree = repomap._to_tree(ranked_tags[:middle], chat_rel_fnames)
        num_tokens = repomap.token_count(tree)
        pct_err = abs(num_tokens - max_map_tokens) / max_map_tokens

        if (num_tokens <= max_map_tokens and num_tokens > best_tree_tokens) or pct_err < 0.15:
            best_tree = tree
            best_tree_tokens = num_tokens
            if pct_err < 0.15:
                break

        if num_tokens < max_map_tokens:
            lower_bound = middle + 1
        else:
            upper_bound = middle - 1
        middle = (lower_bound + upper_bound) // 2

    return best_tree


def get_ranked_tags_map_uncached(
    repomap,
    chat_fnames,
    other_fnames=None,
    max_map_tokens=None,
    mentioned_fnames=None,
    mentioned_idents=None,
):
    other_fnames, max_map_tokens, mentioned_fnames, mentioned_idents = _normalized_rank_inputs(
        repomap,
        other_fnames,
        max_map_tokens,
        mentioned_fnames,
        mentioned_idents,
    )

    spinner = Spinner(repomap.update_message)
    ranked_tags = repomap.get_ranked_tags(
        chat_fnames,
        other_fnames,
        mentioned_fnames,
        mentioned_idents,
        progress=spinner.step,
    )
    ranked_tags = _prepend_special_fnames(repomap, ranked_tags, other_fnames)

    spinner.step()
    chat_rel_fnames = {repomap._get_rel_fname(fname) for fname in chat_fnames}
    repomap.tree_cache = {}
    best_tree = _find_best_tree(
        repomap,
        ranked_tags,
        chat_rel_fnames,
        max_map_tokens,
        spinner,
    )
    spinner.end()
    return best_tree
