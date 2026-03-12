"""Common types/utilities for file rankers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Set, Tuple

try:
    from ..repomap_adapter import check_repomap_available

    _REPOMAP_CHECK_AVAILABLE = True
except ImportError:
    _REPOMAP_CHECK_AVAILABLE = False


def is_repomap_available(root: Path = None) -> bool:
    """Check if RepoMap is available (lazy evaluation)."""
    if not _REPOMAP_CHECK_AVAILABLE:
        return False
    available, _ = check_repomap_available(root)
    return available


class FileRanker(ABC):
    """Abstract interface for file ranking strategies."""

    @abstractmethod
    def rank_files(
        self,
        files: List[str],
        focus_files: List[str] = None,
        mentioned_files: Set[str] = None,
    ) -> List[Tuple[str, float]]:
        """Rank files by importance."""
        raise NotImplementedError


__all__ = ["FileRanker", "is_repomap_available"]
