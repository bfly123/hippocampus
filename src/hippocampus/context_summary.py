"""Tiered index summarization for proxy injection.

Generates compact text summaries from hippocampus index data at three tiers:
- Tier A (~500 tokens): Project overview + module list only
- Tier B (~2000 tokens): + key files, dependencies, architecture
- Tier C (~4000 tokens): + file details, signatures, full dependency graph
"""

from __future__ import annotations

from .constants import CHARS_PER_TOKEN


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _truncate(text: str, max_tokens: int) -> str:
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 20] + "\n... (truncated)"


def summarize_index(index: dict, tier: str = "B", max_tokens: int = 0) -> str:
    """Generate a tiered summary of the hippocampus index.

    Args:
        index: Parsed hippocampus-index.json data.
        tier: "A" (~500 tok), "B" (~2000 tok), or "C" (~4000 tok).
        max_tokens: Override max tokens (0 = use tier default).
    """
    tier = tier.upper()
    if max_tokens <= 0:
        max_tokens = {"A": 500, "B": 2000, "C": 4000}.get(tier, 2000)

    parts: list[str] = []

    # ── Project overview (all tiers) ──────────────────────────────
    project = index.get("project", {})
    stats = index.get("stats", {})
    if isinstance(project, dict):
        overview = project.get("overview", "")
        arch = project.get("architecture", "")
    else:
        overview = str(project)
        arch = ""

    parts.append(f"# Project Context (hippocampus index)")
    if overview:
        parts.append(f"\n{overview}")
    parts.append(
        f"\nScale: {stats.get('total_files', 0)} files, "
        f"{stats.get('total_modules', 0)} modules, "
        f"{stats.get('total_signatures', 0)} signatures"
    )

    # ── Module list (all tiers) ───────────────────────────────────
    modules = index.get("modules", [])
    parts.append("\n## Modules")
    for m in modules:
        line = f"- {m['id']} [{m.get('tier', '?')}/{m.get('role', '?')}] files={m.get('file_count', 0)}"
        desc = m.get("desc", "")
        if desc:
            # Tier A: short desc; B/C: longer
            max_desc = 60 if tier == "A" else 120
            line += f" — {desc[:max_desc]}"
        parts.append(line)

    if tier == "A":
        return _truncate("\n".join(parts), max_tokens)

    # ── Architecture (tier B+) ────────────────────────────────────
    if arch:
        parts.append(f"\n## Architecture\n{arch[:500]}")

    # ── Key files per module (tier B+) ────────────────────────────
    parts.append("\n## Key Files")
    for m in modules:
        key_files = m.get("key_files", [])
        if key_files:
            files_str = ", ".join(key_files[:5])
            parts.append(f"- {m['id']}: {files_str}")

    # ── Module dependencies (tier B+) ─────────────────────────────
    mod_deps = index.get("module_dependencies", {})
    if mod_deps:
        parts.append("\n## Module Dependencies")
        for src, deps in mod_deps.items():
            targets = ", ".join(f"{d['target']}" for d in deps[:5])
            parts.append(f"  {src} → {targets}")

    if tier == "B":
        return _truncate("\n".join(parts), max_tokens)

    # ── File details (tier C) ─────────────────────────────────────
    files = index.get("files", {})
    parts.append("\n## File Details")
    for fpath, fdata in list(files.items())[:50]:
        desc = fdata.get("desc", "")
        tags = fdata.get("tags", [])
        sigs = fdata.get("signatures", [])
        line = f"- {fpath}"
        if desc:
            line += f": {desc[:80]}"
        if tags:
            line += f" [{', '.join(tags[:4])}]"
        if sigs:
            sig_names = [s.get("name", "") for s in sigs[:5]]
            line += f" sigs: {', '.join(sig_names)}"
        parts.append(line)

    return _truncate("\n".join(parts), max_tokens)


def summarize_architect_report(report: dict, max_tokens: int = 500) -> str:
    """Summarize an architect-report.json into compact text."""
    parts: list[str] = []

    mode = report.get("mode", "unknown")
    score = report.get("score", "?")
    parts.append(f"\n## Architect Report ({mode}, score={score})")

    # Rule findings
    findings = report.get("rule_findings", [])
    if findings:
        parts.append("Findings:")
        for f in findings[:10]:
            sev = f.get("severity", "?")
            parts.append(f"  - [{sev}] {f.get('rule_id', '?')}: {f.get('message', '')[:100]}")

    # LLM analysis summary
    llm = report.get("llm_analysis", {})
    if llm:
        summary = llm.get("summary", "")
        if summary:
            parts.append(f"Assessment: {summary[:200]}")
        recs = llm.get("recommendations", [])
        if recs:
            parts.append("Recommendations:")
            for r in recs[:5]:
                parts.append(f"  - [{r.get('priority', '?')}] {r.get('action', '')[:80]}")

    return _truncate("\n".join(parts), max_tokens)
