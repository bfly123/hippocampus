"""Cache helpers for embedded RepoMap."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from diskcache import Cache


def handle_tags_cache_error(repomap, sqlite_errors, original_error=None) -> None:
    if repomap.verbose and original_error:
        repomap.io.tool_warning(f"Tags cache error: {str(original_error)}")

    if isinstance(getattr(repomap, "TAGS_CACHE", None), dict):
        return

    path = Path(repomap.root) / repomap.TAGS_CACHE_DIR
    try:
        if path.exists():
            shutil.rmtree(path)

        new_cache = Cache(path)
        test_key = "test"
        new_cache[test_key] = "test"
        _ = new_cache[test_key]
        del new_cache[test_key]
        repomap.TAGS_CACHE = new_cache
        return
    except sqlite_errors as err:
        repomap.io.tool_warning(
            f"Unable to use tags cache at {path}, falling back to memory cache"
        )
        if repomap.verbose:
            repomap.io.tool_warning(f"Cache recreation error: {str(err)}")

    repomap.TAGS_CACHE = {}


def load_tags_cache(repomap, sqlite_errors) -> None:
    path = Path(repomap.root) / repomap.TAGS_CACHE_DIR
    try:
        repomap.TAGS_CACHE = Cache(path)
    except sqlite_errors as err:
        handle_tags_cache_error(repomap, sqlite_errors, err)


def get_mtime(repomap, fname: str):
    try:
        return os.path.getmtime(fname)
    except FileNotFoundError:
        repomap.io.tool_warning(f"File not found error: {fname}")
        return None


def _cache_get(repomap, cache_key: str, sqlite_errors):
    try:
        return repomap.TAGS_CACHE.get(cache_key)
    except sqlite_errors as err:
        handle_tags_cache_error(repomap, sqlite_errors, err)
        return repomap.TAGS_CACHE.get(cache_key)


def get_tags(repomap, fname: str, rel_fname: str, sqlite_errors):
    file_mtime = get_mtime(repomap, fname)
    if file_mtime is None:
        return []

    cache_key = fname
    cached_value = _cache_get(repomap, cache_key, sqlite_errors)
    if cached_value is not None and cached_value.get("mtime") == file_mtime:
        try:
            return repomap.TAGS_CACHE[cache_key]["data"]
        except sqlite_errors as err:
            handle_tags_cache_error(repomap, sqlite_errors, err)
            return repomap.TAGS_CACHE[cache_key]["data"]

    data = list(repomap._get_tags_raw(fname, rel_fname))
    try:
        repomap.TAGS_CACHE[cache_key] = {"mtime": file_mtime, "data": data}
        repomap._save_tags_cache()
    except sqlite_errors as err:
        handle_tags_cache_error(repomap, sqlite_errors, err)
        repomap.TAGS_CACHE[cache_key] = {"mtime": file_mtime, "data": data}
    return data
