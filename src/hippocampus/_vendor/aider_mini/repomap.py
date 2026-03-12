"""Embedded RepoMap implementation adapted from aider for hippocampus."""

from __future__ import annotations

import sqlite3

from .repomap_cache import (
    get_tags as get_tags_impl,
    handle_tags_cache_error,
    load_tags_cache,
)
from .repomap_graph import get_ranked_tags as get_ranked_tags_impl
from .repomap_map import (
    get_ranked_tags_map as get_ranked_tags_map_impl,
    get_ranked_tags_map_uncached as get_ranked_tags_map_uncached_impl,
)
from .repomap_repo import build_repo_map
from .repomap_render import render_tree as render_tree_impl, to_tree as to_tree_impl
from .repomap_tags import Tag, USING_TSL_PACK, get_tags_raw as get_tags_raw_impl, load_query_scm

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - progress bar is optional
    def tqdm(iterable, **_kwargs):
        return iterable


SQLITE_ERRORS = (sqlite3.OperationalError, sqlite3.DatabaseError, OSError)

CACHE_VERSION = 101 if USING_TSL_PACK else 100
UPDATING_REPO_MAP_MESSAGE = "Updating repo map"


class RepoMap:
    TAGS_CACHE_DIR = f".aider.tags.cache.v{CACHE_VERSION}"
    warned_files = set()
    sqlite_errors = SQLITE_ERRORS
    progress_bar = staticmethod(tqdm)
    update_message = UPDATING_REPO_MAP_MESSAGE

    def __init__(
        self,
        map_tokens=1024,
        root=None,
        main_model=None,
        io=None,
        repo_content_prefix=None,
        verbose=False,
        max_context_window=None,
        map_mul_no_files=8,
        refresh="auto",
    ):
        self.io = io
        self.verbose = verbose
        self.refresh = refresh
        self.root = root or __import__("os").getcwd()
        self._load_tags_cache()
        self.cache_threshold = 0.95
        self.max_map_tokens = map_tokens
        self.map_mul_no_files = map_mul_no_files
        self.max_context_window = max_context_window
        self.repo_content_prefix = repo_content_prefix
        self.main_model = main_model
        self.tree_cache = {}
        self.tree_context_cache = {}
        self.map_cache = {}
        self.map_processing_time = 0
        self.last_map = None

        if self.verbose:
            self.io.tool_output(
                f"RepoMap initialized with map_mul_no_files: {self.map_mul_no_files}"
            )

    def token_count(self, text):
        text_length = len(text)
        if text_length < 200:
            return self.main_model.token_count(text)

        lines = text.splitlines(keepends=True)
        sampled_lines = lines[:: (len(lines) // 100 or 1)]
        sample_text = "".join(sampled_lines)
        sample_tokens = self.main_model.token_count(sample_text)
        return sample_tokens / len(sample_text) * text_length

    def get_repo_map(
        self,
        chat_files,
        other_files,
        mentioned_fnames=None,
        mentioned_idents=None,
        force_refresh=False,
    ):
        return build_repo_map(
            self,
            chat_files,
            other_files,
            mentioned_fnames=mentioned_fnames or set(),
            mentioned_idents=mentioned_idents or set(),
            force_refresh=force_refresh,
        )

    def _get_rel_fname(self, fname):
        try:
            return __import__("os").path.relpath(fname, self.root)
        except ValueError:
            return fname

    def _tags_cache_error(self, original_error=None):
        handle_tags_cache_error(self, self.sqlite_errors, original_error)

    def _load_tags_cache(self):
        load_tags_cache(self, self.sqlite_errors)

    def _save_tags_cache(self):
        return None

    def get_tags(self, fname, rel_fname):
        return get_tags_impl(self, fname, rel_fname, self.sqlite_errors)

    def _get_tags_raw(self, fname, rel_fname):
        return get_tags_raw_impl(self, fname, rel_fname)

    def get_ranked_tags(
        self, chat_fnames, other_fnames, mentioned_fnames, mentioned_idents, progress=None
    ):
        return get_ranked_tags_impl(
            self,
            chat_fnames,
            other_fnames,
            mentioned_fnames,
            mentioned_idents,
            progress=progress,
        )

    def _get_ranked_tags_map(
        self,
        chat_fnames,
        other_fnames=None,
        max_map_tokens=None,
        mentioned_fnames=None,
        mentioned_idents=None,
        force_refresh=False,
    ):
        return get_ranked_tags_map_impl(
            self,
            chat_fnames,
            other_fnames,
            max_map_tokens,
            mentioned_fnames,
            mentioned_idents,
            force_refresh,
        )

    def _get_ranked_tags_map_uncached(
        self,
        chat_fnames,
        other_fnames=None,
        max_map_tokens=None,
        mentioned_fnames=None,
        mentioned_idents=None,
    ):
        return get_ranked_tags_map_uncached_impl(
            self,
            chat_fnames,
            other_fnames,
            max_map_tokens,
            mentioned_fnames,
            mentioned_idents,
        )

    def _get_mtime(self, fname):
        from .repomap_cache import get_mtime

        return get_mtime(self, fname)

    def render_tree(self, abs_fname, rel_fname, lois):
        return render_tree_impl(self, abs_fname, rel_fname, lois)

    def _to_tree(self, tags, chat_rel_fnames):
        return to_tree_impl(self, tags, chat_rel_fnames)


__all__ = ["RepoMap", "Tag", "load_query_scm"]
