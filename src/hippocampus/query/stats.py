"""Index stats — structural statistics and ASCII visualization."""

from __future__ import annotations

from typing import Any

from ..utils import estimate_tokens


def _module_distribution(index: dict) -> list[dict]:
    """Compute per-module file count, signature count, and tier."""
    modules = index.get("modules", [])
    files = index.get("files", {})

    result = []
    for mod in modules:
        mid = mod["id"]
        mod_files = [
            (fp, fd) for fp, fd in files.items()
            if fd.get("module") == mid
        ]
        sig_count = sum(
            len(fd.get("signatures", []))
            for _, fd in mod_files
        )
        result.append({
            "id": mid,
            "tier": mod.get("tier", ""),
            "file_count": len(mod_files),
            "sig_count": sig_count,
        })

    result.sort(key=lambda m: m["file_count"], reverse=True)
    return result


def _tag_frequency(index: dict) -> list[tuple[str, int]]:
    """Count tag occurrences across all files, sorted descending."""
    files = index.get("files", {})
    counts: dict[str, int] = {}
    for fd in files.values():
        for tag in fd.get("tags", []):
            counts[tag] = counts.get(tag, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)


def _top_files(index: dict, n: int = 5) -> list[dict]:
    """Return top N files by signature count."""
    files = index.get("files", {})
    ranked = []
    for fp, fd in files.items():
        ranked.append({
            "path": fp,
            "sig_count": len(fd.get("signatures", [])),
            "module": fd.get("module", ""),
        })
    ranked.sort(key=lambda x: (-x["sig_count"], x["path"]))
    return ranked[:n]


def _render_bar(label: str, value: int, max_value: int, width: int = 30) -> str:
    """Render a single ASCII bar chart line."""
    if max_value <= 0:
        filled = 0
    else:
        filled = round(value / max_value * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"  {label:<20s} {bar} {value}"


_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def _render_sparkline(values: list[int | float]) -> str:
    """Map a list of numeric values to a sparkline string."""
    if not values:
        return ""
    lo = min(values)
    hi = max(values)
    span = hi - lo
    if span == 0:
        return _SPARK_CHARS[4] * len(values)
    result = []
    for v in values:
        idx = int((v - lo) / span * (len(_SPARK_CHARS) - 1))
        result.append(_SPARK_CHARS[idx])
    return "".join(result)


def build_stats(index: dict[str, Any]) -> dict[str, Any]:
    """Build structural statistics for the current index.

    Returns dict with modules, tier_summary, top_files, tag_freq,
    consumed_tokens, and Markdown content.
    """
    modules = _module_distribution(index)
    tag_freq = _tag_frequency(index)
    top_files = _top_files(index)

    # Tier summary
    tier_summary: dict[str, int] = {"core": 0, "secondary": 0, "peripheral": 0}
    for m in modules:
        tier = m.get("tier", "")
        if tier in tier_summary:
            tier_summary[tier] += 1

    # Render Markdown
    lines = ["# Index Statistics", ""]

    # Module distribution bar chart
    if modules:
        lines.append("## Module Distribution (by file count)")
        lines.append("")
        max_fc = max(m["file_count"] for m in modules) if modules else 1
        for m in modules:
            lines.append(_render_bar(m["id"], m["file_count"], max_fc))
        lines.append("")

    # Tier summary
    lines.append("## Tier Summary")
    lines.append("")
    for tier, count in tier_summary.items():
        lines.append(f"- **{tier}**: {count} modules")
    lines.append("")

    # Top files
    if top_files:
        lines.append("## Top Files (by signature count)")
        lines.append("")
        for f in top_files:
            lines.append(f"- `{f['path']}` ({f['sig_count']} sigs) [{f['module']}]")
        lines.append("")

    # Tag frequency
    if tag_freq:
        lines.append("## Tag Frequency (top 10)")
        lines.append("")
        for tag, count in tag_freq[:10]:
            lines.append(f"- `{tag}`: {count}")
        lines.append("")

    content = "\n".join(lines)

    return {
        "modules": modules,
        "tier_summary": tier_summary,
        "top_files": top_files,
        "tag_freq": tag_freq,
        "consumed_tokens": estimate_tokens(content),
        "content": content,
    }


def build_stats_history(snapshots: list[dict]) -> dict[str, Any]:
    """Build cross-version trend from snapshot summaries.

    Args:
        snapshots: list of dicts with "generated_at" and "stats" keys,
                   ordered oldest-first.

    Returns dict with sparklines and Markdown content.
    Falls back to empty content if fewer than 2 snapshots.
    """
    if len(snapshots) < 2:
        return {
            "snapshots_count": len(snapshots),
            "consumed_tokens": 0,
            "content": "",
        }

    # Extract time series (oldest first)
    dates = [s.get("generated_at", "?") for s in snapshots]
    files_series = [s.get("stats", {}).get("total_files", 0) for s in snapshots]
    mods_series = [s.get("stats", {}).get("total_modules", 0) for s in snapshots]
    sigs_series = [s.get("stats", {}).get("total_signatures", 0) for s in snapshots]

    lines = ["# Index History", ""]
    lines.append(f"**Snapshots**: {len(snapshots)}")
    lines.append(f"**Range**: {dates[0]} → {dates[-1]}")
    lines.append("")

    lines.append("## Trends")
    lines.append("")
    lines.append(f"- Files:      {_render_sparkline(files_series)}  "
                 f"({files_series[0]} → {files_series[-1]})")
    lines.append(f"- Modules:    {_render_sparkline(mods_series)}  "
                 f"({mods_series[0]} → {mods_series[-1]})")
    lines.append(f"- Signatures: {_render_sparkline(sigs_series)}  "
                 f"({sigs_series[0]} → {sigs_series[-1]})")
    lines.append("")

    content = "\n".join(lines)

    return {
        "snapshots_count": len(snapshots),
        "consumed_tokens": estimate_tokens(content),
        "content": content,
    }
