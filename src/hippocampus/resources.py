"""Packaged static resources used by install/runtime flows."""

from __future__ import annotations

from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path
import shutil
from typing import Iterator


@contextmanager
def packaged_queries_dir() -> Iterator[Path]:
    """Yield a filesystem path for packaged query assets."""
    queries = files("hippocampus").joinpath("resources", "queries")
    with as_file(queries) as local_path:
        yield Path(local_path)


def copy_packaged_queries(destination: Path) -> int:
    """Copy packaged query assets into a project .hippocampus/queries dir."""
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    with packaged_queries_dir() as queries_dir:
        if not queries_dir.exists():
            return copied
        for scm in queries_dir.glob("*.scm"):
            dst = destination / scm.name
            if dst.exists():
                continue
            shutil.copy2(scm, dst)
            copied += 1
    return copied


__all__ = ["copy_packaged_queries", "packaged_queries_dir"]
