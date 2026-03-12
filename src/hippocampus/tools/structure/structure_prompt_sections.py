from __future__ import annotations

from collections import Counter
from typing import Any

from ...utils import estimate_tokens
from .structure_prompt_ranking import (
    is_noise_file_path,
    module_sort_key,
    rank_source_files,
    rank_test_files,
)


def _render_ranked_file_entry(file_path: str, file_data: dict[str, Any], *, include_symbols: bool) -> str:
    desc = file_data.get("desc", "")
    sig_count = len(file_data.get("signatures", []))
    entry = f"- `{file_path}`"
    if desc:
        entry += f": {desc}"
    if include_symbols and sig_count:
        entry += f" ({sig_count} symbols)"
    return entry


def _append_ranked_file_entries(
    lines: list[str],
    ranked_files,
    *,
    remaining_budget: int,
    file_cap: int,
    include_symbols: bool,
) -> tuple[int, int]:
    added = 0
    for item in ranked_files:
        if added >= file_cap:
            break
        file_path, file_data = item[:2]
        entry = _render_ranked_file_entry(file_path, file_data, include_symbols=include_symbols)
        cost = estimate_tokens(entry + "\n")
        if remaining_budget - cost < 0:
            break
        lines.append(entry)
        remaining_budget -= cost
        added += 1
    return remaining_budget, added


def _render_signature_entry(
    file_path: str,
    signatures: list[dict[str, Any]],
) -> str:
    signature_labels = [f"{sig.get('kind', '?')} {sig.get('name', '?')}" for sig in signatures]
    return f"- `{file_path}`: {', '.join(signature_labels)}"


def render_l1(modules: list[dict[str, Any]], *, module_lines: int) -> str:
    lines = ["## Modules", ""]
    sorted_mods = sorted(modules, key=module_sort_key)
    for mod in sorted_mods[:module_lines]:
        module_id = mod.get("id", "?").removeprefix("mod:")
        desc = mod.get("desc", "")
        file_count = mod.get("file_count", 0)
        tier = mod.get("tier", "")
        score = mod.get("core_score", 0)
        tier_label = f" [{tier}]" if tier else ""
        lines.append(f"- **{module_id}**{tier_label} (score={score:.2f}, {file_count} files): {desc}")
    if len(sorted_mods) > module_lines:
        lines.append(f"- ... (+{len(sorted_mods) - module_lines} more modules)")
    lines.append("")
    return "\n".join(lines)


def render_l2(
    modules: list[dict[str, Any]],
    files: dict[str, dict],
    file_roles: dict[str, str],
    *,
    source_budget: int,
    test_budget: int,
    key_files_cap: int,
    test_files_cap: int,
) -> str:
    lines = ["## Key Files", ""]
    _remaining_src, source_added = _append_ranked_file_entries(
        lines,
        rank_source_files(modules, files, file_roles),
        remaining_budget=source_budget,
        file_cap=key_files_cap,
        include_symbols=True,
    )
    if source_added == 0:
        lines.append("- No source files selected under current budget.")

    test_files = rank_test_files(files, file_roles)
    if test_files and test_budget > 0:
        lines.extend(["", "### Test Files", ""])
        _remaining_test, test_added = _append_ranked_file_entries(
            lines,
            test_files,
            remaining_budget=test_budget,
            file_cap=test_files_cap,
            include_symbols=True,
        )
        if len(test_files) > test_added:
            lines.append(f"- ... (+{len(test_files) - test_added} more test files)")

    lines.append("")
    return "\n".join(lines)


def render_l3(
    modules: list[dict[str, Any]],
    files: dict[str, dict],
    file_roles: dict[str, str],
    *,
    budget: int,
    max_sigs_per_file: int,
    signature_files_cap: int,
) -> str:
    lines = ["## Signatures", ""]
    remaining = budget
    added = 0

    for file_path, file_data, _score in rank_source_files(modules, files, file_roles):
        if added >= signature_files_cap:
            break
        signatures = file_data.get("signatures", [])
        if not signatures:
            continue
        signatures = signatures[:max_sigs_per_file]
        entry = _render_signature_entry(file_path, signatures)
        entry_tokens = estimate_tokens(entry + "\n")
        if remaining - entry_tokens < 0:
            break
        lines.append(entry)
        remaining -= entry_tokens
        added += 1

    if added == 0:
        lines.append("- No signatures selected under current budget.")

    lines.append("")
    return "\n".join(lines)


def render_changes(diff_data: dict[str, Any]) -> str:
    changes = []
    for entry in diff_data.get("changes", []):
        path = str(entry.get("id", "")).split(":", 1)[-1]
        if path and is_noise_file_path(path):
            continue
        changes.append(entry)

    if not changes:
        return ""

    counts: Counter[str] = Counter()
    for entry in changes:
        counts[entry.get("change", "unknown")] += 1

    lines = [
        "## Recent Changes",
        "",
        f"**Summary**: {', '.join(f'{value} {key}' for key, value in sorted(counts.items()))}",
        "",
    ]
    for entry in changes[:40]:
        lines.append(f"- [{entry.get('change', '?')}] {entry.get('name', entry.get('id', '?'))}")
    if len(changes) > 40:
        lines.append(f"- ... (+{len(changes) - 40} more changes)")
    lines.append("")
    return "\n".join(lines)
