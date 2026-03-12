"""Assembly helpers for structure prompt generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...constants import INDEX_FILE, STRUCTURE_PROMPT_FILE, TREE_DIFF_FILE, TREE_FILE
from ...types import TreeNode
from ...utils import estimate_tokens, read_json, write_text
from .structure_prompt_assemble_support import (
    append_directory_tree,
    append_file_sections,
    append_llm_brief,
    append_project_map,
    append_recent_changes,
)
from .structure_prompt_budget import PromptBudget
from .structure_prompt_profiles import normalize_render_profile, profile_for_budget
from .structure_prompt_roles import classify_file_role
from .structure_prompt_sections import render_l1
from .structure_prompt_tree import truncate_tree
from .structure_strategy import detect_repo_archetype, normalize_archetype


def render_l0_impl(project: dict[str, Any]) -> str:
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


def _load_structure_prompt_inputs(
    output_dir: Path,
) -> tuple[TreeNode, dict[str, Any] | None, dict[str, Any] | None]:
    tree_path = output_dir / TREE_FILE
    if not tree_path.exists():
        raise FileNotFoundError(f"Tree not found: {tree_path}")

    tree_data = read_json(tree_path)
    root = TreeNode(**tree_data["root"])
    index_path = output_dir / INDEX_FILE
    diff_path = output_dir / TREE_DIFF_FILE
    index = read_json(index_path) if index_path.exists() else None
    diff_data = read_json(diff_path) if diff_path.exists() else None
    return root, index, diff_data


def _resolve_archetype(root, *, files, modules, config) -> str:
    archetype = detect_repo_archetype(
        root_name=root.name or ".",
        files=files,
        modules=modules,
    )
    if config is None:
        return archetype
    override = normalize_archetype(getattr(config, "structure_prompt_archetype", None))
    return override if override != "generic" else archetype


def _tree_only_prompt(
    root: TreeNode,
    out_path: Path,
    *,
    max_tokens: int,
    profile: dict[str, Any],
) -> str:
    tree_text = truncate_tree(root, max_tokens * 4, profile=profile)
    markdown = f"# Repository Structure\n\n```\n{tree_text}```\n"
    write_text(out_path, markdown)
    return markdown


def _classify_file_roles(files: dict[str, dict]) -> dict[str, str]:
    return {
        file_path: classify_file_role(file_path, file_data)
        for file_path, file_data in files.items()
    }


def _append_module_section(
    budget: PromptBudget,
    modules: list[dict[str, Any]],
    profile: dict[str, Any],
) -> None:
    if budget.remaining > 0 and modules:
        budget.append_if_fits(
            render_l1(modules, module_lines=int(profile["module_lines"])),
            estimate_tokens,
        )


def _assemble_prompt_sections(
    budget: PromptBudget,
    *,
    project: dict[str, Any],
    root: TreeNode,
    modules: list[dict[str, Any]],
    files: dict[str, dict],
    file_roles: dict[str, str],
    archetype: str,
    profile: dict[str, Any],
    diff_data: dict[str, Any] | None,
    config,
    llm_enhance: bool,
    verbose: bool,
    render_project_map_fn,
    run_async_fn,
    generate_llm_navigation_brief_fn,
    render_llm_navigation_brief_fn,
) -> None:
    append_project_map(
        budget,
        project=project,
        root=root,
        files=files,
        file_roles=file_roles,
        archetype=archetype,
        profile=profile,
        render_project_map_fn=render_project_map_fn,
    )
    if llm_enhance:
        append_llm_brief(
            budget,
            project=project,
            modules=modules,
            files=files,
            file_roles=file_roles,
            config=config,
            archetype=archetype,
            profile=profile,
            verbose=verbose,
            run_async_fn=run_async_fn,
            generate_llm_navigation_brief_fn=generate_llm_navigation_brief_fn,
            render_llm_navigation_brief_fn=render_llm_navigation_brief_fn,
        )
    _append_module_section(budget, modules, profile)
    append_directory_tree(budget, root=root, files=files, profile=profile)
    append_file_sections(
        budget,
        modules=modules,
        files=files,
        file_roles=file_roles,
        profile=profile,
        diff_data=diff_data,
    )
    append_recent_changes(budget, diff_data=diff_data)


def run_structure_prompt_impl(
    output_dir: Path,
    *,
    max_tokens: int,
    verbose: bool,
    config,
    llm_enhance: bool,
    render_profile: str,
    output_name: str | None,
    render_project_map_fn,
    run_async_fn,
    generate_llm_navigation_brief_fn,
    render_llm_navigation_brief_fn,
) -> str:
    profile_mode = normalize_render_profile(render_profile)
    profile = profile_for_budget(max_tokens, render_profile=profile_mode)
    out_path = output_dir / (output_name or STRUCTURE_PROMPT_FILE)
    root, index, diff_data = _load_structure_prompt_inputs(output_dir)

    if index is None:
        return _tree_only_prompt(root, out_path, max_tokens=max_tokens, profile=profile)

    project = index.get("project", {})
    modules = index.get("modules", [])
    files = index.get("files", {})
    file_roles = _classify_file_roles(files) if files else {}
    archetype = _resolve_archetype(root, files=files, modules=modules, config=config)

    budget = PromptBudget(remaining=max_tokens)
    l0_text = render_l0_impl(project)
    budget.parts.append(l0_text)
    budget.remaining -= estimate_tokens(l0_text)
    _assemble_prompt_sections(
        budget,
        project=project,
        root=root,
        modules=modules,
        files=files,
        file_roles=file_roles,
        archetype=archetype,
        profile=profile,
        diff_data=diff_data,
        config=config,
        llm_enhance=llm_enhance,
        verbose=verbose,
        render_project_map_fn=render_project_map_fn,
        run_async_fn=run_async_fn,
        generate_llm_navigation_brief_fn=generate_llm_navigation_brief_fn,
        render_llm_navigation_brief_fn=render_llm_navigation_brief_fn,
    )

    markdown = "\n".join(budget.parts)
    write_text(out_path, markdown)
    if verbose:
        consumed = max_tokens - budget.remaining
        print(
            f"[structure_prompt] profile={profile_mode} "
            f"consumed~{consumed}/{max_tokens} tokens -> {out_path.name}"
        )
    return markdown
