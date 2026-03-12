"""Support helpers for structure prompt assembly."""

from __future__ import annotations

from typing import Any

from ...utils import estimate_tokens
from .structure_prompt_budget import (
    PromptBudget,
    compute_role_budgets,
    compute_tree_budget_tokens,
)
from .structure_prompt_roles import ROLE_SOURCE, ROLE_TEST
from .structure_prompt_sections import render_changes, render_l2, render_l3
from .structure_prompt_tree import truncate_tree


def append_project_map(
    budget: PromptBudget,
    *,
    project: dict[str, Any],
    root,
    files: dict[str, dict],
    file_roles: dict[str, str],
    archetype: str,
    profile: dict[str, Any],
    render_project_map_fn,
) -> None:
    if budget.remaining <= 0 or not files:
        return
    map_text = render_project_map_fn(
        project,
        root,
        files,
        file_roles,
        archetype=archetype,
        profile=profile,
    )
    map_tokens = estimate_tokens(map_text)
    if map_tokens <= budget.remaining:
        budget.parts.append(map_text)
        budget.remaining -= map_tokens


def append_llm_brief(
    budget: PromptBudget,
    *,
    project: dict[str, Any],
    modules: list[dict[str, Any]],
    files: dict[str, dict],
    file_roles: dict[str, str],
    config,
    archetype: str,
    profile: dict[str, Any],
    verbose: bool,
    run_async_fn,
    generate_llm_navigation_brief_fn,
    render_llm_navigation_brief_fn,
) -> None:
    if not _should_append_llm_brief(budget, files, config, profile):
        return
    brief = _load_llm_brief(
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
    )
    if brief:
        budget.append_if_fits(
            render_llm_navigation_brief_fn(brief, profile=profile),
            estimate_tokens,
        )


def _should_append_llm_brief(
    budget: PromptBudget,
    files: dict[str, dict],
    config,
    profile: dict[str, Any],
) -> bool:
    return (
        config is not None
        and budget.remaining > 0
        and bool(files)
        and bool(profile.get("include_llm_brief", True))
    )


def _load_llm_brief(
    *,
    project: dict[str, Any],
    modules: list[dict[str, Any]],
    files: dict[str, dict],
    file_roles: dict[str, str],
    config,
    archetype: str,
    profile: dict[str, Any],
    verbose: bool,
    run_async_fn,
    generate_llm_navigation_brief_fn,
) -> dict[str, Any] | None:
    try:
        return run_async_fn(
            generate_llm_navigation_brief_fn(
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
        if verbose:
            print(f"[structure_prompt] llm brief skipped: {exc}")
        return None


def append_directory_tree(
    budget: PromptBudget,
    *,
    root,
    files: dict[str, dict],
    profile: dict[str, Any],
) -> None:
    if budget.remaining <= 0:
        return
    tree_budget_tokens = compute_tree_budget_tokens(
        remaining=budget.remaining,
        has_files=bool(files),
        profile=profile,
    )
    tree_text = truncate_tree(root, max(600, tree_budget_tokens * 4), profile=profile)
    tree_block = f"## Directory Tree\n\n```\n{tree_text}```\n"
    tree_tokens = estimate_tokens(tree_block)
    if tree_tokens <= budget.remaining:
        budget.parts.append(tree_block)
        budget.remaining -= tree_tokens


def append_file_sections(
    budget: PromptBudget,
    *,
    modules: list[dict[str, Any]],
    files: dict[str, dict],
    file_roles: dict[str, str],
    profile: dict[str, Any],
    diff_data: dict[str, Any] | None,
) -> None:
    if budget.remaining <= 0 or not files:
        return

    section_budgets = _file_section_budgets(budget.remaining, file_roles, profile, diff_data)
    _append_l2_section(
        budget,
        modules=modules,
        files=files,
        file_roles=file_roles,
        profile=profile,
        source_l2=section_budgets["source_l2"],
        test_l2=section_budgets["test_l2"],
    )
    _append_l3_section(
        budget,
        modules=modules,
        files=files,
        file_roles=file_roles,
        profile=profile,
        source_l3=section_budgets["source_l3"],
    )


def _file_section_budgets(
    remaining: int,
    file_roles: dict[str, str],
    profile: dict[str, Any],
    diff_data: dict[str, Any] | None,
) -> dict[str, int]:
    changes_reserve = 220 if diff_data else 0
    role_budgets = compute_role_budgets(max(0, remaining - changes_reserve), file_roles)
    source_total = role_budgets.get(ROLE_SOURCE, 0)
    source_l2 = int(source_total * float(profile["prefer_l2_ratio"]))
    return {
        "source_l2": source_l2,
        "source_l3": source_total - source_l2,
        "test_l2": role_budgets.get(ROLE_TEST, 0),
    }


def _append_l2_section(
    budget: PromptBudget,
    *,
    modules: list[dict[str, Any]],
    files: dict[str, dict],
    file_roles: dict[str, str],
    profile: dict[str, Any],
    source_l2: int,
    test_l2: int,
) -> None:
    l2_text = render_l2(
        modules,
        files,
        file_roles,
        source_budget=source_l2,
        test_budget=test_l2,
        key_files_cap=int(profile["key_files"]),
        test_files_cap=int(profile["test_files"]),
    )
    _append_if_fit(budget, l2_text)


def _append_l3_section(
    budget: PromptBudget,
    *,
    modules: list[dict[str, Any]],
    files: dict[str, dict],
    file_roles: dict[str, str],
    profile: dict[str, Any],
    source_l3: int,
) -> None:
    if not (
        source_l3 > 0
        and budget.remaining > 0
        and bool(profile.get("include_signatures", True))
    ):
        return
    l3_text = render_l3(
        modules,
        files,
        file_roles,
        budget=min(source_l3, budget.remaining),
        max_sigs_per_file=int(profile["sigs_per_file"]),
        signature_files_cap=int(profile["signature_files"]),
    )
    _append_if_fit(budget, l3_text)


def _append_if_fit(budget: PromptBudget, text: str) -> None:
    tokens = estimate_tokens(text)
    if text.strip() and tokens <= budget.remaining:
        budget.parts.append(text)
        budget.remaining -= tokens


def append_recent_changes(
    budget: PromptBudget,
    *,
    diff_data: dict[str, Any] | None,
) -> None:
    if budget.remaining <= 0 or not diff_data:
        return
    changes_text = render_changes(diff_data)
    if not changes_text:
        return
    changes_tokens = estimate_tokens(changes_text)
    if changes_tokens <= budget.remaining:
        budget.parts.append(changes_text)
        budget.remaining -= changes_tokens
