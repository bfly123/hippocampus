"""
Conversation context extraction for automatic navigation.

Extracts file mentions and identifiers from conversation history
to drive task-relevant context generation.
"""

from collections import deque
from pathlib import Path
import re
from typing import Dict, Set


def _tokenize_path_words(text: str) -> tuple[Set[str], Set[str]]:
    words = {
        word.rstrip(",.!;:?").strip("\"'`*_")
        for word in text.split()
    }
    normalized_words = {word.replace("\\", "/") for word in words}
    return words, normalized_words


def _collect_full_path_mentions(
    normalized_words: Set[str],
    all_files: Set[str],
) -> Set[str]:
    mentioned: Set[str] = set()
    for file in all_files:
        normalized_file = file.replace("\\", "/")
        if normalized_file in normalized_words:
            mentioned.add(file)
    return mentioned


def _build_unique_basename_map(all_files: Set[str]) -> Dict[str, list[str]]:
    basename_map: Dict[str, list[str]] = {}
    for file in all_files:
        basename = Path(file).name
        if "/" in file or "." in basename or "_" in basename or "-" in basename:
            basename_map.setdefault(basename, []).append(file)
    return basename_map


def _collect_unique_basename_mentions(
    words: Set[str],
    basename_map: Dict[str, list[str]],
) -> Set[str]:
    mentioned: Set[str] = set()
    for basename, files in basename_map.items():
        if len(files) == 1 and basename in words:
            mentioned.add(files[0])
    return mentioned


def extract_file_mentions(text: str, all_files: Set[str]) -> Set[str]:
    """
    Extract file mentions from text.

    Args:
        text: Input text (user message or conversation)
        all_files: Set of all tracked files in the repository

    Returns:
        Set of mentioned file paths
    """
    words, normalized_words = _tokenize_path_words(text)
    mentioned = _collect_full_path_mentions(normalized_words, all_files)
    basename_map = _build_unique_basename_map(all_files)
    mentioned.update(_collect_unique_basename_mentions(words, basename_map))
    return mentioned


def extract_idents(text: str) -> Set[str]:
    """
    Extract identifiers from text.

    Args:
        text: Input text

    Returns:
        Set of identifiers (alphanumeric tokens)
    """
    # Split on non-word characters and filter out empty strings
    idents = set(re.split(r"\W+", text))
    return {i for i in idents if i and len(i) > 1}


class WorkingMemory:
    """
    Tracks recent conversation context with time decay.

    Maintains a sliding window of recent messages and tracks
    file mentions with exponential decay to handle context drift.
    """

    def __init__(self, window_size: int = 10, decay_factor: float = 0.8):
        """
        Initialize working memory.

        Args:
            window_size: Number of recent messages to keep
            decay_factor: Exponential decay factor for file weights (0-1)
        """
        self.recent_messages: deque = deque(maxlen=window_size)
        self.chat_files: Dict[str, float] = {}  # {file: weight}
        self.decay_factor = decay_factor
        self.message_count = 0

    def add_message(self, text: str, all_files: Set[str]):
        """
        Add a message and update working files with time decay.

        Args:
            text: Message text
            all_files: Set of all tracked files
        """
        self.recent_messages.append(text)
        self.message_count += 1

        # Decay existing file weights
        for file in list(self.chat_files.keys()):
            self.chat_files[file] *= self.decay_factor
            # Remove files with very low weight
            if self.chat_files[file] < 0.01:
                del self.chat_files[file]

        # Add newly mentioned files with weight 1.0
        mentioned = extract_file_mentions(text, all_files)
        for file in mentioned:
            self.chat_files[file] = 1.0

    def get_context_text(self) -> str:
        """Get aggregated text from recent messages."""
        return "\n".join(self.recent_messages)

    def get_active_files(self, threshold: float = 0.1) -> Set[str]:
        """Get active files with weight >= threshold."""
        return {f for f, w in self.chat_files.items() if w >= threshold}

    def reset(self):
        """Reset working memory."""
        self.chat_files.clear()
        self.recent_messages.clear()
        self.message_count = 0
