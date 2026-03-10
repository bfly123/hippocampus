"""Main runner for structure prompt generation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..constants import INDEX_FILE, TREE_DIFF_FILE, STRUCTURE_PROMPT_FILE, TREE_FILE
from ..types import TreeNode
from ..utils import estimate_tokens, read_json, write_text
from .structure_strategy import detect_repo_archetype, normalize_archetype
from .structure_prompt_budget import (
    PromptBudget,
    compute_role_budgets,
    compute_tree_budget_tokens,
)
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
from .structure_prompt_roles import classify_file_role, ROLE_SOURCE, ROLE_TEST
from .structure_prompt_sections import render_changes, render_l1, render_l2, render_l3
from .structure_prompt_tree import skip_dir, truncate_tree

if TYPE_CHECKING:
    from ..config import HippoConfig


def render_l0(project: dict[str, Any]) -> str:
    lines = ["# Repository Structure", ""]
    overview = project.get("overview", "")
    if overview:
        lines.append(overview)
        lines.append("")
    arch = project.get("architecture", "")
    if arch:
        lines.append(f"**Architecture**: {arch}")
        lines.append("")
    scale = project.get("scale", {})
    if scale:
        lines.append(
            f"**Scale**: {scale.get('files', '?')} files, "
            f"{scale.get('modules', '?')} modules, "
            f"primary language: {scale.get('primary_lang', '?')}"
        )
        lines.append("")
    return "\n".join(lines)


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
    profile_mode = normalize_render_profile(render_profile)
    profile = profile_for_budget(max_tokens, render_profile=profile_mode)
    out_file_name = output_name or STRUCTURE_PROMPT_FILE
    out_path = output_dir / out_file_name

    tree_path = output_dir / TREE_FILE
    if not tree_path.exists():
        raise FileNotFoundError(f"Tree not found: {tree_path}")

    tree_data = read_json(tree_path)
    root = TreeNode(**tree_data["root"])

    index_path = output_dir / INDEX_FILE
    index: dict[str, Any] | None = read_json(index_path) if index_path.exists() else None

    diff_path = output_dir / TREE_DIFF_FILE
    diff_data: dict[str, Any] | None = read_json(diff_path) if diff_path.exists() else None

    if index is None:
        tree_text = truncate_tree(root, max_tokens * 4, profile=profile)
        md = f"# Repository Structure\n\n```\n{tree_text}```\n"
        write_text(out_path, md)
        return md

    project = index.get("project", {})
    modules = index.get("modules", [])
    files = index.get("files", {})
    file_roles = {fp: classify_file_role(fp, fd) for fp, fd in files.items()} if files else {}
    root_name = root.name or "."
    archetype = detect_repo_archetype(root_name=root_name, files=files, modules=modules)
    if config is not None:
        override = normalize_archetype(getattr(config, "structure_prompt_archetype", None))
        if override != "generic":
            archetype = override

    budget = PromptBudget(remaining=max_tokens)
    parts = budget.parts

    l0_text = render_l0(project)
    l0_tokens = estimate_tokens(l0_text)
    parts.append(l0_text)
    budget.remaining -= l0_tokens

    if budget.remaining > 0 and files:
        map_text = render_project_map(
            project, root, files, file_roles, archetype=archetype, profile=profile
        )
        map_tokens = estimate_tokens(map_text)
        if map_tokens <= budget.remaining:
            parts.append(map_text)
            budget.remaining -= map_tokens

    if (
        llm_enhance
        and bool(profile.get("include_llm_brief", True))
        and config is not None
        and budget.remaining > 0
        and files
    ):
        try:
            brief = run_async(
                generate_llm_navigation_brief(
                    project=project,
                    modules=modules,
                    files=files,
                    file_roles=file_roles,
                    config=config,
                    archetype=archetype,
                    profile=profile,
                )
            )
        except Exception as exc:
            brief = None
            if verbose:
                print(f"[structure_prompt] llm brief skipped: {exc}")
        if brief:
            brief_text = render_llm_navigation_brief(brief, profile=profile)
            budget.append_if_fits(brief_text, estimate_tokens)

    if budget.remaining > 0 and modules:
        l1_text = render_l1(modules, module_lines=int(profile["module_lines"]))
        budget.append_if_fits(l1_text, estimate_tokens)

    if budget.remaining > 0:
        tree_budget_tokens = compute_tree_budget_tokens(
            remaining=budget.remaining,
            has_files=bool(files),
            profile=profile,
        )
        tree_char_budget = max(600, tree_budget_tokens * 4)
        tree_text = truncate_tree(root, tree_char_budget, profile=profile)
        tree_block = f"## Directory Tree\n\n```\n{tree_text}```\n"
        tree_tokens = estimate_tokens(tree_block)
        if tree_tokens <= budget.remaining:
            parts.append(tree_block)
            budget.remaining -= tree_tokens

    if budget.remaining > 0 and files:
        changes_reserve = 220 if diff_data else 0
        l2l3_budget = max(0, budget.remaining - changes_reserve)
        role_budgets = compute_role_budgets(l2l3_budget, file_roles)
        src_total = role_budgets.get(ROLE_SOURCE, 0)
        src_l2 = int(src_total * float(profile["prefer_l2_ratio"]))
        src_l3 = src_total - src_l2
        test_l2 = role_budgets.get(ROLE_TEST, 0)

        l2_text = render_l2(
            modules,
            files,
            file_roles,
            source_budget=src_l2,
            test_budget=test_l2,
            key_files_cap=int(profile["key_files"]),
            test_files_cap=int(profile["test_files"]),
        )
        l2_tokens = estimate_tokens(l2_text)
        if l2_text.strip() and l2_tokens <= budget.remaining:
            parts.append(l2_text)
            budget.remaining -= l2_tokens

        if src_l3 > 0 and budget.remaining > 0 and bool(profile.get("include_signatures", True)):
            l3_text = render_l3(
                modules,
                files,
                file_roles,
                budget=min(src_l3, budget.remaining),
                max_sigs_per_file=int(profile["sigs_per_file"]),
                signature_files_cap=int(profile["signature_files"]),
            )
            l3_tokens = estimate_tokens(l3_text)
            if l3_text.strip() and l3_tokens <= budget.remaining:
                parts.append(l3_text)
                budget.remaining -= l3_tokens

    if budget.remaining > 0 and diff_data:
        changes_text = render_changes(diff_data)
        if changes_text:
            changes_tokens = estimate_tokens(changes_text)
            if changes_tokens <= budget.remaining:
                parts.append(changes_text)
                budget.remaining -= changes_tokens

    md = "\n".join(parts)
    write_text(out_path, md)

    if verbose:
        consumed = max_tokens - budget.remaining
        print(
            f"[structure_prompt] profile={profile_mode} "
            f"consumed~{consumed}/{max_tokens} tokens -> {out_path.name}"
        )
    return md
