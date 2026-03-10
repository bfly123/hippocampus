from __future__ import annotations

from collections import Counter
from typing import Any

from ..utils import estimate_tokens
from .structure_prompt_ranking import (
    is_noise_file_path,
    module_sort_key,
    rank_source_files,
    rank_test_files,
)


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
    remaining_src = source_budget
    source_added = 0

    for file_path, file_data, _score in rank_source_files(modules, files, file_roles):
        if source_added >= key_files_cap:
            break
        desc = file_data.get("desc", "")
        sig_count = len(file_data.get("signatures", []))
        entry = f"- `{file_path}`"
        if desc:
            entry += f": {desc}"
        if sig_count:
            entry += f" ({sig_count} symbols)"
        cost = estimate_tokens(entry + "\n")
        if remaining_src - cost < 0:
            break
        lines.append(entry)
        remaining_src -= cost
        source_added += 1

    if source_added == 0:
        lines.append("- No source files selected under current budget.")

    test_files = rank_test_files(files, file_roles)
    if test_files and test_budget > 0:
        lines.extend(["", "### Test Files", ""])
        remaining_test = test_budget
        test_added = 0
        for file_path, file_data in test_files:
            if test_added >= test_files_cap:
                break
            desc = file_data.get("desc", "")
            symbols = len(file_data.get("signatures", []))
            entry = f"- `{file_path}`"
            if desc:
                entry += f": {desc}"
            entry += f" ({symbols} symbols)"
            cost = estimate_tokens(entry + "\n")
            if remaining_test - cost < 0:
                break
            lines.append(entry)
            remaining_test -= cost
            test_added += 1
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
        signature_labels = [f"{sig.get('kind', '?')} {sig.get('name', '?')}" for sig in signatures]
        entry = f"- `{file_path}`: {', '.join(signature_labels)}"
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
