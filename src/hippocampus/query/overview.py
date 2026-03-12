"""hippo_overview — budget-aware layered project overview.

Renders hippocampus-index.json as Markdown in three layers:
  L0: Project overview (always included)
  L1: Module summaries (by core_score descending)
  L2: File lists for core modules (budget permitting)

Usage:
  result = build_overview(index, budget=4000)
  print(result["content"])
"""

from __future__ import annotations

from typing import Any

from ..utils import estimate_tokens


def _render_l0(project: dict) -> str:
    """Render L0: project-level overview."""
    lines = ["# Project Overview", ""]
    overview = project.get("overview", "")
    if overview:
        lines.append(overview)
        lines.append("")
    arch = project.get("architecture", "")
    if arch:
        lines.append("## Architecture")
        lines.append("")
        lines.append(arch)
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


def _render_l1(mod: dict) -> str:
    """Render L1: single module summary line."""
    mid = mod.get("id", "?")
    desc = mod.get("desc", "")
    tier = mod.get("tier", "")
    score = mod.get("core_score", 0)
    fc = mod.get("file_count", 0)
    tier_label = f" [{tier}]" if tier else ""
    return (
        f"- **{mid}**{tier_label} "
        f"(score={score:.2f}, {fc} files): {desc}"
    )


def _render_l2_files(mod: dict, files: dict[str, dict]) -> str:
    """Render L2: file list for a module."""
    mid = mod.get("id", "")
    mod_files = [
        (fp, fd) for fp, fd in files.items()
        if fd.get("module") == mid
    ]
    if not mod_files:
        return ""

    # Sort by number of signatures descending (more complex = more important)
    mod_files.sort(key=lambda x: len(x[1].get("signatures", [])), reverse=True)

    lines = [f"  **{mid}** files:"]
    for fp, fd in mod_files:
        desc = fd.get("desc", "")
        sig_count = len(fd.get("signatures", []))
        suffix = f" ({sig_count} sigs)" if sig_count else ""
        lines.append(f"    - `{fp}`{suffix}: {desc}")
    return "\n".join(lines)


def _sorted_modules_by_score(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        modules,
        key=lambda module: module.get("core_score", 0),
        reverse=True,
    )


def _render_l1_section(
    sorted_mods: list[dict[str, Any]],
    remaining: int,
) -> tuple[str | None, int]:
    if remaining <= 0 or not sorted_mods:
        return None, remaining

    lines = ["## Modules", ""]
    added = False
    for mod in sorted_mods:
        line = _render_l1(mod)
        line_tokens = estimate_tokens(line + "\n")
        if remaining - line_tokens < 0:
            break
        lines.append(line)
        remaining -= line_tokens
        added = True
    if not added:
        return None, remaining
    lines.append("")
    return "\n".join(lines), remaining


def _render_l2_section(
    sorted_mods: list[dict[str, Any]],
    files: dict[str, dict],
    remaining: int,
) -> tuple[str | None, int]:
    if remaining <= 0:
        return None, remaining

    blocks: list[str] = []
    for mod in sorted_mods:
        if mod.get("tier") != "core":
            continue
        block = _render_l2_files(mod, files)
        if not block:
            continue
        block_tokens = estimate_tokens(block + "\n")
        if remaining - block_tokens < 0:
            break
        blocks.append(block)
        remaining -= block_tokens

    if not blocks:
        return None, remaining

    header = "## Core Module Files\n\n"
    header_tokens = estimate_tokens(header)
    if remaining < header_tokens:
        return None, remaining
    remaining -= header_tokens
    return header + "\n".join(blocks) + "\n", remaining


def build_overview(
    index: dict[str, Any],
    budget: int = 4000,
) -> dict[str, Any]:
    """Build a budget-aware layered overview.

    Returns dict with:
      content: str          — Markdown text
      consumed_tokens: int  — estimated tokens used
      layers_included: list — which layers were included
    """
    project = index.get("project", {})
    modules = index.get("modules", [])
    files = index.get("files", {})
    sorted_mods = _sorted_modules_by_score(modules)

    parts: list[str] = []
    layers: list[str] = []
    remaining = budget

    # L0: always included
    l0_text = _render_l0(project)
    l0_tokens = estimate_tokens(l0_text)
    parts.append(l0_text)
    remaining -= l0_tokens
    layers.append("L0")

    l1_section, remaining = _render_l1_section(sorted_mods, remaining)
    if l1_section:
        parts.append(l1_section)
        layers.append("L1")

    l2_section, remaining = _render_l2_section(sorted_mods, files, remaining)
    if l2_section:
        parts.append(l2_section)
        layers.append("L2")

    content = "\n".join(parts)
    consumed = budget - remaining

    return {
        "content": content,
        "consumed_tokens": consumed,
        "layers_included": layers,
    }
