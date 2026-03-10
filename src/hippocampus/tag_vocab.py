"""Tag vocabulary system — closed vocab + rolling expansion.

Implements design doc §6.3-6.5: four-dimension base vocab,
rolling expansion for new tags, and validation enforcement.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .constants import HIPPO_DIR, TAG_VOCAB_FILE
from .utils import read_json, write_json


# New tag naming rule: lowercase, hyphens allowed, max 15 chars
_TAG_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,14}$")


def is_valid_new_tag(tag: str) -> bool:
    """Check if a proposed new tag meets naming rules.

    Rules: all lowercase, hyphens allowed, 1-15 characters,
    must start with a letter.
    """
    return bool(_TAG_PATTERN.match(tag))


def default_vocab() -> dict[str, list[str]]:
    """Return the built-in four-dimension base vocabulary."""
    return {
        "role": [
            "entrypoint", "lib", "config", "test",
            "docs", "ci", "script", "asset",
        ],
        "domain": [
            "cli", "api", "ui", "auth", "i18n",
            "mail", "memory", "terminal", "web", "mcp",
        ],
        "pattern": [
            "daemon", "adapter", "parser", "formatter",
            "handler", "provider", "util",
        ],
        "tech": [
            "python", "shell", "javascript", "typescript",
            "yaml", "css", "go", "rust", "java", "ruby",
            "c", "cpp",
        ],
    }


class TagVocab:
    """Closed vocabulary + rolling expansion manager."""

    def __init__(self, base_vocab: dict[str, list[str]]) -> None:
        self._vocab: dict[str, list[str]] = {
            dim: list(tags) for dim, tags in base_vocab.items()
        }
        # Build flat lookup set
        self._flat: set[str] = set()
        for tags in self._vocab.values():
            self._flat.update(tags)

    def all_tags(self) -> set[str]:
        """Return all tags across all dimensions."""
        return set(self._flat)

    def contains(self, tag: str) -> bool:
        """Check if a tag exists in the vocabulary."""
        return tag in self._flat

    def add_tag(self, tag: str, dimension: str = "custom") -> bool:
        """Add a new tag via rolling expansion.

        Returns True if the tag was added, False if it already
        exists or fails naming validation.
        """
        if tag in self._flat:
            return False
        if not is_valid_new_tag(tag):
            return False
        self._vocab.setdefault(dimension, []).append(tag)
        self._flat.add(tag)
        return True

    def validate_tags(
        self, tags: list[str],
    ) -> tuple[list[str], list[str]]:
        """Split tags into (valid, invalid) based on current vocab."""
        valid = [t for t in tags if t in self._flat]
        invalid = [t for t in tags if t not in self._flat]
        return valid, invalid

    def content_hash(self) -> str:
        """Deterministic hash of current vocab for cache invalidation."""
        # Sort dimensions and tags for determinism
        canonical = json.dumps(
            {k: sorted(v) for k, v in sorted(self._vocab.items())},
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def snapshot(self) -> dict[str, list[str]]:
        """Serialize current vocabulary (including rolling expansions)."""
        return {
            dim: list(tags) for dim, tags in self._vocab.items()
        }

    def format_for_prompt(self) -> str:
        """Format vocabulary as a readable string for LLM prompts."""
        lines = []
        for dim, tags in self._vocab.items():
            lines.append(f"  {dim}: {', '.join(sorted(tags))}")
        return "\n".join(lines)


def load_vocab(output_dir: Path) -> TagVocab:
    """Load vocabulary from tag-vocab.json, or create from defaults."""
    vocab_path = output_dir / TAG_VOCAB_FILE
    if vocab_path.exists():
        data = read_json(vocab_path)
        return TagVocab(data)
    return TagVocab(default_vocab())


def save_vocab(output_dir: Path, vocab: TagVocab) -> None:
    """Persist current vocabulary (including rolling expansions)."""
    vocab_path = output_dir / TAG_VOCAB_FILE
    write_json(vocab_path, vocab.snapshot())
