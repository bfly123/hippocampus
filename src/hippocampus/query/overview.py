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

    # Sort modules by core_score descending
    sorted_mods = sorted(
        modules,
        key=lambda m: m.get("core_score", 0),
        reverse=True,
    )

    parts: list[str] = []
    layers: list[str] = []
    remaining = budget

    # L0: always included
    l0_text = _render_l0(project)
    l0_tokens = estimate_tokens(l0_text)
    parts.append(l0_text)
    remaining -= l0_tokens
    layers.append("L0")

    # L1: module summaries (by score)
    if remaining > 0 and sorted_mods:
        l1_lines = ["## Modules", ""]
        l1_added = False
        for mod in sorted_mods:
            line = _render_l1(mod)
            line_tokens = estimate_tokens(line + "\n")
            if remaining - line_tokens < 0:
                break
            l1_lines.append(line)
            remaining -= line_tokens
            l1_added = True
        if l1_added:
            l1_lines.append("")
            parts.append("\n".join(l1_lines))
            layers.append("L1")

    # L2: file lists for core modules only
    if remaining > 0:
        l2_parts: list[str] = []
        l2_added = False
        for mod in sorted_mods:
            if mod.get("tier") != "core":
                continue
            block = _render_l2_files(mod, files)
            if not block:
                continue
            block_tokens = estimate_tokens(block + "\n")
            if remaining - block_tokens < 0:
                break
            l2_parts.append(block)
            remaining -= block_tokens
            l2_added = True
        if l2_added:
            header = "## Core Module Files\n\n"
            header_tokens = estimate_tokens(header)
            if remaining >= header_tokens:
                remaining -= header_tokens
                parts.append(header + "\n".join(l2_parts) + "\n")
                layers.append("L2")

    content = "\n".join(parts)
    consumed = budget - remaining

    return {
        "content": content,
        "consumed_tokens": consumed,
        "layers_included": layers,
    }
