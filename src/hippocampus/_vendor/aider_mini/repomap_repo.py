"""Repo content assembly helpers for embedded RepoMap."""

from __future__ import annotations


def _effective_map_tokens(repomap, chat_files) -> int:
    max_map_tokens = repomap.max_map_tokens
    if not (max_map_tokens and repomap.max_context_window):
        return max_map_tokens

    padding = 4096
    expanded_target = min(
        int(max_map_tokens * repomap.map_mul_no_files),
        repomap.max_context_window - padding,
    )
    if not chat_files and expanded_target > 0:
        return expanded_target
    return max_map_tokens


def _repo_prefix(repomap, chat_files) -> str:
    if not repomap.repo_content_prefix:
        return ""
    other = "other " if chat_files else ""
    return repomap.repo_content_prefix.format(other=other)


def build_repo_map(
    repomap,
    chat_files,
    other_files,
    *,
    mentioned_fnames,
    mentioned_idents,
    force_refresh: bool,
):
    if repomap.max_map_tokens <= 0 or not other_files:
        return None

    try:
        files_listing = repomap._get_ranked_tags_map(
            chat_files,
            other_files,
            _effective_map_tokens(repomap, chat_files),
            mentioned_fnames,
            mentioned_idents,
            force_refresh,
        )
    except RecursionError:
        repomap.io.tool_error("Disabling repo map, git repo too large?")
        repomap.max_map_tokens = 0
        return None

    if not files_listing:
        return None

    if repomap.verbose:
        num_tokens = repomap.token_count(files_listing)
        repomap.io.tool_output(f"Repo-map: {num_tokens / 1024:.1f} k-tokens")

    return _repo_prefix(repomap, chat_files) + files_listing
