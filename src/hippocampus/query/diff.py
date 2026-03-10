"""Index diff — compare two index versions and produce structured change summary."""

from __future__ import annotations

from typing import Any

from ..utils import estimate_tokens


def _match_modules(
    old_mods: list[dict],
    old_files: dict[str, dict],
    new_mods: list[dict],
    new_files: dict[str, dict],
) -> dict:
    """Match old modules to new modules using file-set Jaccard similarity.

    Returns dict with:
      matched: [(old_mod, new_mod, jaccard), ...]
      added:   [new_mod, ...]
      removed: [old_mod, ...]
    """
    THRESHOLD = 0.3

    # Build file sets per module
    def _file_set(files: dict, mod_id: str) -> set[str]:
        return {fp for fp, fd in files.items() if fd.get("module") == mod_id}

    old_sets = {m["id"]: _file_set(old_files, m["id"]) for m in old_mods}
    new_sets = {m["id"]: _file_set(new_files, m["id"]) for m in new_mods}

    matched = []
    used_new = set()

    for om in old_mods:
        oid = om["id"]
        oset = old_sets[oid]
        best_nid = None
        best_jaccard = 0.0

        for nm in new_mods:
            nid = nm["id"]
            if nid in used_new:
                continue
            nset = new_sets[nid]
            union = oset | nset
            if not union:
                continue
            jaccard = len(oset & nset) / len(union)
            if jaccard > best_jaccard:
                best_jaccard = jaccard
                best_nid = nid

        if best_nid and best_jaccard >= THRESHOLD:
            new_mod = next(m for m in new_mods if m["id"] == best_nid)
            matched.append((om, new_mod, best_jaccard))
            used_new.add(best_nid)

    matched_old_ids = {om["id"] for om, _, _ in matched}
    removed = [m for m in old_mods if m["id"] not in matched_old_ids]
    added = [m for m in new_mods if m["id"] not in used_new]

    return {"matched": matched, "added": added, "removed": removed}


def _diff_stats(old_index: dict, new_index: dict) -> dict:
    """Compute delta between stats fields."""
    old_s = old_index.get("stats", {})
    new_s = new_index.get("stats", {})
    return {
        "files": new_s.get("total_files", 0) - old_s.get("total_files", 0),
        "modules": new_s.get("total_modules", 0) - old_s.get("total_modules", 0),
        "signatures": (
            new_s.get("total_signatures", 0) - old_s.get("total_signatures", 0)
        ),
    }


def _diff_modules(old_index: dict, new_index: dict, module_match: dict) -> dict:
    """Compute module-level changes."""
    modules_added = [
        {"id": m["id"], "desc": m.get("desc", "")}
        for m in module_match["added"]
    ]
    modules_removed = [
        {"id": m["id"], "desc": m.get("desc", "")}
        for m in module_match["removed"]
    ]
    modules_changed = [
        {"old_id": om["id"], "new_id": nm["id"], "jaccard": round(j, 3)}
        for om, nm, j in module_match["matched"]
    ]
    return {
        "modules_added": modules_added,
        "modules_removed": modules_removed,
        "modules_changed": modules_changed,
    }


def _diff_files(old_index: dict, new_index: dict, module_match: dict | None = None) -> dict:
    """Compute file-level changes.

    If module_match is provided, module renames (matched pairs) are normalized
    so that a file staying in a renamed module is not reported as "moved".
    """
    old_files = old_index.get("files", {})
    new_files = new_index.get("files", {})

    # Build old→new module ID mapping from matched pairs
    mod_rename: dict[str, str] = {}
    if module_match:
        for om, nm, _ in module_match.get("matched", []):
            mod_rename[om["id"]] = nm["id"]

    old_paths = set(old_files)
    new_paths = set(new_files)

    files_added = sorted(new_paths - old_paths)
    files_removed = sorted(old_paths - new_paths)

    # Files present in both — check module moves and tag changes
    common = old_paths & new_paths
    files_moved = []
    files_tag_changed = []

    for fp in sorted(common):
        of = old_files[fp]
        nf = new_files[fp]

        # Module move — normalize via rename map to avoid false moves
        old_mod = of.get("module", "")
        new_mod = nf.get("module", "")
        normalized_old = mod_rename.get(old_mod, old_mod)
        if normalized_old != new_mod:
            files_moved.append({
                "path": fp,
                "old_module": old_mod,
                "new_module": new_mod,
            })

        # Tag changes
        old_tags = set(of.get("tags", []))
        new_tags = set(nf.get("tags", []))
        added_tags = sorted(new_tags - old_tags)
        removed_tags = sorted(old_tags - new_tags)
        if added_tags or removed_tags:
            files_tag_changed.append({
                "path": fp,
                "added": added_tags,
                "removed": removed_tags,
            })

    return {
        "files_added": files_added,
        "files_removed": files_removed,
        "files_moved": files_moved,
        "files_tag_changed": files_tag_changed,
    }


def _render_diff(diff_result: dict) -> str:
    """Render diff result as Markdown."""
    lines = ["# Index Diff", ""]

    # Stats
    sd = diff_result["stats_diff"]
    lines.append("## Stats Changes")
    lines.append("")
    for key in ("files", "modules", "signatures"):
        val = sd[key]
        sign = "+" if val > 0 else ""
        lines.append(f"- **{key}**: {sign}{val}")
    lines.append("")

    # Modules
    ma = diff_result["modules_added"]
    mr = diff_result["modules_removed"]
    mc = diff_result["modules_changed"]
    if ma or mr or mc:
        lines.append("## Module Changes")
        lines.append("")
        for m in ma:
            lines.append(f"- **+ {m['id']}**: {m['desc']}")
        for m in mr:
            lines.append(f"- **- {m['id']}**: {m['desc']}")
        for m in mc:
            lines.append(
                f"- **~ {m['old_id']}** → **{m['new_id']}** "
                f"(jaccard={m['jaccard']:.3f})"
            )
        lines.append("")

    # Files
    fa = diff_result["files_added"]
    fr = diff_result["files_removed"]
    fm = diff_result["files_moved"]
    ft = diff_result["files_tag_changed"]
    if fa or fr or fm or ft:
        lines.append("## File Changes")
        lines.append("")
        for f in fa:
            lines.append(f"- **+** `{f}`")
        for f in fr:
            lines.append(f"- **-** `{f}`")
        for f in fm:
            lines.append(
                f"- **moved** `{f['path']}`: "
                f"{f['old_module']} → {f['new_module']}"
            )
        for f in ft:
            parts = []
            if f["added"]:
                parts.append(f"+[{', '.join(f['added'])}]")
            if f["removed"]:
                parts.append(f"-[{', '.join(f['removed'])}]")
            lines.append(f"- **tags** `{f['path']}`: {' '.join(parts)}")
        lines.append("")

    mag = diff_result["change_magnitude"]
    lines.append(f"**Total change magnitude**: {mag}")
    lines.append("")

    return "\n".join(lines)


def build_diff(
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_id: str = "old",
    new_id: str = "new",
) -> dict[str, Any]:
    """Build a structured diff between two index versions.

    Returns dict with stats_diff, module/file changes, Markdown content.
    """
    old_files = old_index.get("files", {})
    new_files = new_index.get("files", {})
    old_mods = old_index.get("modules", [])
    new_mods = new_index.get("modules", [])

    module_match = _match_modules(old_mods, old_files, new_mods, new_files)
    stats_diff = _diff_stats(old_index, new_index)
    mod_diff = _diff_modules(old_index, new_index, module_match)
    file_diff = _diff_files(old_index, new_index, module_match=module_match)

    change_magnitude = (
        len(file_diff["files_added"])
        + len(file_diff["files_removed"])
        + len(file_diff["files_moved"])
        + len(file_diff["files_tag_changed"])
        + len(mod_diff["modules_added"])
        + len(mod_diff["modules_removed"])
    )

    result = {
        "old_id": old_id,
        "new_id": new_id,
        "stats_diff": stats_diff,
        **mod_diff,
        **file_diff,
        "change_magnitude": change_magnitude,
    }

    content = _render_diff(result)
    result["consumed_tokens"] = estimate_tokens(content)
    result["content"] = content

    return result
