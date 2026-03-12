"""Main runner for structure prompt generation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ...constants import INDEX_FILE, TREE_DIFF_FILE, STRUCTURE_PROMPT_FILE, TREE_FILE
from ...types import TreeNode
from ...utils import read_json
from .structure_prompt_assemble import (
    render_l0_impl,
    run_structure_prompt_impl,
)
from .structure_strategy import detect_repo_archetype, normalize_archetype
from .structure_prompt_navigation import validate_navigation_brief_json as validate_navigation_brief_json_impl
from .structure_prompt_project_map import (
    collect_project_boundaries as collect_project_boundaries_impl,
    generate_llm_navigation_brief as generate_llm_navigation_brief_impl,
    infer_entry_reason as infer_entry_reason_impl,
    rank_code_areas as rank_code_areas_impl,
    rank_entry_files as rank_entry_files_impl,
    render_llm_navigation_brief_profile as render_llm_navigation_brief_impl,
    render_project_map as render_project_map_impl,
    run_async_brief as run_async,
    sanitize_navigation_brief_profile as sanitize_navigation_brief_impl,
)
from .structure_prompt_profiles import (
    _RENDER_PROFILE_AUTO,
    normalize_render_profile,
    profile_for_budget,
)
from .structure_prompt_tree import skip_dir

if TYPE_CHECKING:
    from ...config import HippoConfig


def render_l0(project: dict[str, Any]) -> str:
    return render_l0_impl(project)


def infer_entry_reason(
    file_path: str,
    file_data: dict[str, Any],
    entry_file_reasons: dict[str, str],
) -> tuple[str, float]:
    del file_data
    return infer_entry_reason_impl(file_path, entry_file_reasons)


def rank_entry_files(
    files: dict[str, dict],
    entry_file_reasons: dict[str, str],
) -> list[tuple[str, str, float]]:
    return rank_entry_files_impl(files, entry_file_reasons)


def rank_code_areas(
    files: dict[str, dict], file_roles: dict[str, str]
) -> list[tuple[str, int]]:
    return rank_code_areas_impl(files, file_roles)


def collect_project_boundaries(
    files: dict[str, dict],
    file_roles: dict[str, str],
    entry_files: list[tuple[str, str, float]],
) -> list[dict[str, Any]]:
    return collect_project_boundaries_impl(files, file_roles, entry_files)


async def generate_llm_navigation_brief(
    project: dict[str, Any],
    modules: list[dict[str, Any]],
    files: dict[str, dict],
    file_roles: dict[str, str],
    config: HippoConfig,
    archetype: str,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    return await generate_llm_navigation_brief_impl(
        project,
        modules,
        files,
        file_roles,
        config,
        archetype=archetype,
        profile=profile or {},
    )


def sanitize_navigation_brief(
    data: dict[str, Any],
    known_paths: set[str],
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_profile = profile or profile_for_budget(6000, _RENDER_PROFILE_AUTO)
    return sanitize_navigation_brief_impl(data, known_paths, active_profile)


def validate_navigation_brief_json(text: str, known_paths: set[str]) -> list[str]:
    return validate_navigation_brief_json_impl(text, known_paths)


def render_llm_navigation_brief(
    brief: dict[str, Any],
    profile: dict[str, Any] | None = None,
) -> str:
    active_profile = profile or profile_for_budget(6000, _RENDER_PROFILE_AUTO)
    return render_llm_navigation_brief_impl(brief, active_profile)


def render_project_map(
    project: dict[str, Any],
    root: TreeNode,
    files: dict[str, dict],
    file_roles: dict[str, str],
    archetype: str,
    profile: dict[str, Any] | None = None,
) -> str:
    active_profile = profile or profile_for_budget(6000, _RENDER_PROFILE_AUTO)
    return render_project_map_impl(
        project,
        root,
        files,
        file_roles,
        archetype=archetype,
        profile=active_profile,
        skip_dir_fn=skip_dir,
    )


def run_structure_prompt(
    output_dir: Path,
    max_tokens: int = 10000,
    verbose: bool = False,
    config: HippoConfig | None = None,
    llm_enhance: bool = False,
    render_profile: str = "auto",
    output_name: str | None = None,
) -> str:
    return run_structure_prompt_impl(
        output_dir,
        max_tokens=max_tokens,
        verbose=verbose,
        config=config,
        llm_enhance=llm_enhance,
        render_profile=render_profile,
        output_name=output_name,
        render_project_map_fn=render_project_map,
        run_async_fn=run_async,
        generate_llm_navigation_brief_fn=generate_llm_navigation_brief,
        render_llm_navigation_brief_fn=render_llm_navigation_brief,
    )
