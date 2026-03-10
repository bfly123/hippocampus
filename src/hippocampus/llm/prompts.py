"""Prompt facade backed by external prompt assets."""

from __future__ import annotations

from .prompt_loader import load_prompt_text, render_prompt


def build_phase_1_messages(*, project_root=None, **kwargs) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": load_prompt_text("phase-1-system.md", project_root=project_root)},
        {"role": "user", "content": render_prompt("phase-1-user.md", project_root=project_root, **kwargs)},
    ]


def build_phase_2a_messages(*, project_root=None, **kwargs) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": load_prompt_text("phase-2a-system.md", project_root=project_root)},
        {"role": "user", "content": render_prompt("phase-2a-user.md", project_root=project_root, **kwargs)},
    ]


def build_phase_2b_messages(*, project_root=None, **kwargs) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": load_prompt_text("phase-2b-system.md", project_root=project_root)},
        {"role": "user", "content": render_prompt("phase-2b-user.md", project_root=project_root, **kwargs)},
    ]


def build_phase_3a_messages(*, project_root=None, **kwargs) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": load_prompt_text("phase-3a-system.md", project_root=project_root)},
        {"role": "user", "content": render_prompt("phase-3a-user.md", project_root=project_root, **kwargs)},
    ]


def build_phase_3b_messages(*, project_root=None, **kwargs) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": load_prompt_text("phase-3b-system.md", project_root=project_root)},
        {"role": "user", "content": render_prompt("phase-3b-user.md", project_root=project_root, **kwargs)},
    ]


def build_architect_audit_messages(*, project_root=None, **kwargs) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": load_prompt_text("architect-system.md", project_root=project_root)},
        {"role": "user", "content": render_prompt("architect-audit-user.md", project_root=project_root, **kwargs)},
    ]


def build_architect_review_messages(*, project_root=None, **kwargs) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": load_prompt_text("architect-system.md", project_root=project_root)},
        {"role": "user", "content": render_prompt("architect-review-user.md", project_root=project_root, **kwargs)},
    ]


def build_architect_plan_messages(*, project_root=None, **kwargs) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": load_prompt_text("architect-system.md", project_root=project_root)},
        {"role": "user", "content": render_prompt("architect-plan-user.md", project_root=project_root, **kwargs)},
    ]


__all__ = [
    "build_architect_audit_messages",
    "build_architect_plan_messages",
    "build_architect_review_messages",
    "build_phase_1_messages",
    "build_phase_2a_messages",
    "build_phase_2b_messages",
    "build_phase_3a_messages",
    "build_phase_3b_messages",
    "load_prompt_text",
    "render_prompt",
]
