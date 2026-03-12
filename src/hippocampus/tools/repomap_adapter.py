"""Adapter layer for integrating embedded RepoMap into Hippocampus."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Set, Tuple

from .._vendor.aider_mini import RepoMap
from ..utils import estimate_tokens
from .repomap_availability import check_repomap_available
from .repomap_snippet_extractor import extract_ranked_snippets


class HippoIO:
    """Adapter implementing Aider's IO interface."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.messages = []

    def read_text(self, filename: str, silent: bool = False) -> str | None:
        """Read file content."""
        try:
            path = Path(filename)
            if not path.exists():
                return None
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            if not silent and self.verbose:
                self.tool_warning(f"Failed to read {filename}: {exc}")
            return None

    def tool_error(self, message: str = "") -> None:
        """Log error message."""
        if self.verbose:
            print(f"ERROR: {message}")
        self.messages.append(("error", message))

    def tool_warning(self, message: str = "") -> None:
        """Log warning message."""
        if self.verbose:
            print(f"WARNING: {message}")
        self.messages.append(("warning", message))

    def tool_output(self, message: str = "", **kwargs) -> None:
        """Log output message."""
        if self.verbose:
            print(message)
        self.messages.append(("output", message))


class HippoModel:
    """Adapter providing token counting interface."""

    def token_count(self, text: str) -> int:
        """Estimate token count for text."""
        return estimate_tokens(text)


class HippoRepoMap:
    """Wrapper for Aider RepoMap with path normalization."""

    def __init__(
        self,
        root: Path,
        map_tokens: int = 1024,
        verbose: bool = False,
        index_files: set[str] | None = None,
    ):
        self.root = Path(root).resolve()
        self.verbose = verbose
        self.index_files = index_files or set()

        self.io = HippoIO(verbose=verbose)
        self.model = HippoModel()
        self.repomap = RepoMap(
            map_tokens=map_tokens,
            root=str(self.root),
            main_model=self.model,
            io=self.io,
            verbose=verbose,
        )

    def _normalize_repo_path(self, raw: str) -> str | None:
        if not raw or not isinstance(raw, str):
            return None

        normalized_raw = raw.replace("\\", "/").lstrip("/")
        if Path(normalized_raw).is_absolute():
            return None
        if ".." in normalized_raw.split("/"):
            return None

        try:
            return str(Path(normalized_raw).as_posix())
        except (ValueError, RuntimeError):
            return None

    def _is_indexed_path(self, normalized: str) -> bool:
        if not self.index_files:
            return True
        normalized_lower = normalized.lower()
        return any(
            idx_file.lower() == normalized_lower
            for idx_file in self.index_files
        )

    def _resolve_repo_path(self, normalized: str) -> bool:
        try:
            full_path = (self.root / normalized).resolve()
        except (ValueError, RuntimeError):
            return False
        return full_path.is_relative_to(self.root)

    def _validate_repo_paths(self, files: list[str]) -> list[str]:
        """Validate and filter file paths to ensure they are within the repo."""
        validated = []

        for raw in files:
            normalized = self._normalize_repo_path(raw)
            if normalized is None:
                continue
            if not self._is_indexed_path(normalized):
                continue
            if not self._resolve_repo_path(normalized):
                continue
            validated.append(normalized)

        return validated

    def get_ranked_tags(
        self,
        chat_files: List[str],
        other_files: List[str] = None,
        mentioned_files: Set[str] = None,
        mentioned_idents: Set[str] = None,
    ) -> List[Tuple[str, str, int, str, str]]:
        """Get ranked symbol tags from RepoMap."""
        other_files = other_files or []
        mentioned_files = mentioned_files or set()
        mentioned_idents = mentioned_idents or set()

        chat_files = self._validate_repo_paths(chat_files)
        other_files = self._validate_repo_paths(other_files)
        mentioned_files = set(self._validate_repo_paths(list(mentioned_files)))

        chat_abs = [str(self.root / f) for f in chat_files]
        all_files = sorted(set(chat_files + other_files))
        other_abs = [str(self.root / f) for f in all_files]

        ranked_tags = self.repomap.get_ranked_tags(
            chat_fnames=chat_abs,
            other_fnames=other_abs,
            mentioned_fnames=mentioned_files,
            mentioned_idents=mentioned_idents,
        )

        return ranked_tags

    def get_ranked_snippets(
        self,
        ranked_tags: List[Tuple],
        ranked_files: List[Tuple[str, float]],
        max_snippets_per_file: int = 2,
        global_token_budget: int = 2500,
        per_snippet_token_cap: int = 500,
        mentioned_idents: Set[str] = None,
    ) -> List[dict[str, Any]]:
        """Extract code snippets from ranked tags."""
        return extract_ranked_snippets(
            repomap=self.repomap,
            root=self.root,
            verbose=self.verbose,
            ranked_tags=ranked_tags,
            ranked_files=ranked_files,
            max_snippets_per_file=max_snippets_per_file,
            global_token_budget=global_token_budget,
            per_snippet_token_cap=per_snippet_token_cap,
            mentioned_idents=mentioned_idents,
        )


__all__ = [
    "HippoIO",
    "HippoModel",
    "HippoRepoMap",
    "check_repomap_available",
]
