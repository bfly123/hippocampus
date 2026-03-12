"""Structure prompt facade."""

from __future__ import annotations

from .structure_prompt_profiles import (
    _RENDER_PROFILE_AUTO,
    _RENDER_PROFILE_DEEP,
    _RENDER_PROFILE_MAP,
    _RENDER_PROFILE_VALUES,
    normalize_render_profile as _normalize_render_profile,
    profile_for_budget as _profile_for_budget,
)
from .structure_prompt_roles import (
    ROLE_CONFIG,
    ROLE_DOCS,
    ROLE_SOURCE,
    ROLE_TEST,
    classify_file_role,
)
from .structure_prompt_runner import (
    render_llm_navigation_brief as _render_llm_navigation_brief,
    run_structure_prompt,
    sanitize_navigation_brief as _sanitize_navigation_brief,
    validate_navigation_brief_json as _validate_navigation_brief_json,
)
from .structure_prompt_tree import (
    render_node as _render_node,
    truncate_tree as _truncate_tree,
)

__all__ = [
    "ROLE_CONFIG",
    "ROLE_DOCS",
    "ROLE_SOURCE",
    "ROLE_TEST",
    "_RENDER_PROFILE_AUTO",
    "_RENDER_PROFILE_DEEP",
    "_RENDER_PROFILE_MAP",
    "_RENDER_PROFILE_VALUES",
    "_normalize_render_profile",
    "_profile_for_budget",
    "_render_llm_navigation_brief",
    "_render_node",
    "_sanitize_navigation_brief",
    "_truncate_tree",
    "_validate_navigation_brief_json",
    "classify_file_role",
    "run_structure_prompt",
]
