"""
Navigation Plane - Working Memory for Task-Driven Code Context

Provides query-driven, incremental context generation for specific tasks,
complementing the macro-level structure analysis.
"""

from .conversation import WorkingMemory, extract_file_mentions, extract_idents
from .extractor import extract_tags_cached, Tag
from .graph import rank_files_tiered
from .context import render_context, allocate_token_budget
from .navigate import navigate, NavigateResult, extract_mentions

__all__ = [
    "WorkingMemory",
    "extract_file_mentions",
    "extract_idents",
    "extract_tags_cached",
    "Tag",
    "rank_files_tiered",
    "render_context",
    "allocate_token_budget",
    "navigate",
    "NavigateResult",
    "extract_mentions",
]
