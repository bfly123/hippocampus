"""Tiered index summarization for proxy injection."""

from __future__ import annotations

from .constants import CHARS_PER_TOKEN

_TIER_DEFAULTS = {"A": 500, "B": 2000, "C": 4000}


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _truncate(text: str, max_tokens: int) -> str:
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20] + "\n... (truncated)"


def _project_overview_lines(index: dict) -> tuple[list[str], str, list[dict]]:
    project = index.get("project", {})
    stats = index.get("stats", {})
    if isinstance(project, dict):
        overview = project.get("overview", "")
        architecture = project.get("architecture", "")
    else:
        overview = str(project)
        architecture = ""

    lines = ["# Project Context (hippocampus index)"]
    if overview:
        lines.append(f"\n{overview}")
    lines.append(
        f"\nScale: {stats.get('total_files', 0)} files, "
        f"{stats.get('total_modules', 0)} modules, "
        f"{stats.get('total_signatures', 0)} signatures"
    )
    return lines, architecture, index.get("modules", [])


def _append_module_lines(parts: list[str], modules: list[dict], *, tier: str) -> None:
    parts.append("\n## Modules")
    max_desc = 60 if tier == "A" else 120
    for module in modules:
        line = (
            f"- {module['id']} [{module.get('tier', '?')}/{module.get('role', '?')}] "
            f"files={module.get('file_count', 0)}"
        )
        desc = module.get("desc", "")
        if desc:
            line += f" — {desc[:max_desc]}"
        parts.append(line)


def _append_tier_b_sections(parts: list[str], *, architecture: str, modules: list[dict], index: dict) -> None:
    if architecture:
        parts.append(f"\n## Architecture\n{architecture[:500]}")

    parts.append("\n## Key Files")
    for module in modules:
        key_files = module.get("key_files", [])
        if key_files:
            parts.append(f"- {module['id']}: {', '.join(key_files[:5])}")

    module_dependencies = index.get("module_dependencies", {})
    if module_dependencies:
        parts.append("\n## Module Dependencies")
        for source, deps in module_dependencies.items():
            parts.append(f"  {source} → {', '.join(dep['target'] for dep in deps[:5])}")


def _append_tier_c_sections(parts: list[str], index: dict) -> None:
    parts.append("\n## File Details")
    for file_path, file_data in list(index.get("files", {}).items())[:50]:
        parts.append(_file_detail_line(file_path, file_data))


def _file_detail_line(file_path: str, file_data: dict) -> str:
    line = f"- {file_path}"
    desc = file_data.get("desc", "")
    tags = file_data.get("tags", [])
    signatures = file_data.get("signatures", [])
    if desc:
        line += f": {desc[:80]}"
    if tags:
        line += f" [{', '.join(tags[:4])}]"
    if signatures:
        sig_names = [signature.get("name", "") for signature in signatures[:5]]
        line += f" sigs: {', '.join(sig_names)}"
    return line


def summarize_index(index: dict, tier: str = "B", max_tokens: int = 0) -> str:
    """Generate a tiered summary of the hippocampus index."""
    tier = tier.upper()
    max_tokens = max_tokens or _TIER_DEFAULTS.get(tier, 2000)

    parts, architecture, modules = _project_overview_lines(index)
    _append_module_lines(parts, modules, tier=tier)
    if tier == "A":
        return _truncate("\n".join(parts), max_tokens)

    _append_tier_b_sections(parts, architecture=architecture, modules=modules, index=index)
    if tier == "B":
        return _truncate("\n".join(parts), max_tokens)

    _append_tier_c_sections(parts, index)
    return _truncate("\n".join(parts), max_tokens)


def summarize_architect_report(report: dict, max_tokens: int = 500) -> str:
    """Summarize an architect-report.json into compact text."""
    parts = [f"\n## Architect Report ({report.get('mode', 'unknown')}, score={report.get('score', '?')})"]
    findings = report.get("rule_findings", [])
    if findings:
        parts.append("Findings:")
        for finding in findings[:10]:
            severity = finding.get("severity", "?")
            parts.append(
                f"  - [{severity}] {finding.get('rule_id', '?')}: "
                f"{finding.get('message', '')[:100]}"
            )

    llm = report.get("llm_analysis", {})
    if llm:
        summary = llm.get("summary", "")
        if summary:
            parts.append(f"Assessment: {summary[:200]}")
        recommendations = llm.get("recommendations", [])
        if recommendations:
            parts.append("Recommendations:")
            for recommendation in recommendations[:5]:
                parts.append(
                    f"  - [{recommendation.get('priority', '?')}] "
                    f"{recommendation.get('action', '')[:80]}"
                )
    return _truncate("\n".join(parts), max_tokens)
