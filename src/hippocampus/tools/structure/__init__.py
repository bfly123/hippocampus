"""Structure-prompt implementation package."""

from .structure_prompt import run_structure_prompt
from .structure_strategy import detect_repo_archetype, normalize_archetype

__all__ = [
    "detect_repo_archetype",
    "normalize_archetype",
    "run_structure_prompt",
]
