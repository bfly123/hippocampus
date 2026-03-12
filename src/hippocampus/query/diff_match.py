"""Matching helpers for index diff computations."""

from __future__ import annotations

from typing import Any


def file_set(files: dict, module_id: str) -> set[str]:
    return {file_path for file_path, file_data in files.items() if file_data.get("module") == module_id}


def best_module_match(
    source_set: set[str],
    new_modules: list[dict],
    new_sets: dict[str, set[str]],
    used_new: set[str],
) -> tuple[str | None, float]:
    best_module_id = None
    best_jaccard = 0.0
    for module in new_modules:
        module_id = module["id"]
        if module_id in used_new:
            continue
        target_set = new_sets[module_id]
        union = source_set | target_set
        if not union:
            continue
        jaccard = len(source_set & target_set) / len(union)
        if jaccard > best_jaccard:
            best_jaccard = jaccard
            best_module_id = module_id
    return best_module_id, best_jaccard


def _match_old_modules(
    old_modules: list[dict],
    new_modules: list[dict],
    *,
    old_sets: dict[str, set[str]],
    new_sets: dict[str, set[str]],
    threshold: float,
    used_new: set[str],
) -> list[tuple[dict, dict, float]]:
    matched: list[tuple[dict, dict, float]] = []
    new_mod_by_id = {module["id"]: module for module in new_modules}
    for old_module in old_modules:
        best_nid, best_jaccard = best_module_match(
            old_sets[old_module["id"]],
            new_modules,
            new_sets,
            used_new,
        )
        if not best_nid or best_jaccard < threshold:
            continue
        matched.append((old_module, new_mod_by_id[best_nid], best_jaccard))
        used_new.add(best_nid)
    return matched


def match_modules(
    old_modules: list[dict],
    old_files: dict[str, dict],
    new_modules: list[dict],
    new_files: dict[str, dict],
) -> dict[str, Any]:
    threshold = 0.3
    old_sets = {module["id"]: file_set(old_files, module["id"]) for module in old_modules}
    new_sets = {module["id"]: file_set(new_files, module["id"]) for module in new_modules}
    used_new: set[str] = set()
    matched = _match_old_modules(
        old_modules,
        new_modules,
        old_sets=old_sets,
        new_sets=new_sets,
        threshold=threshold,
        used_new=used_new,
    )
    matched_old_ids = {old_module["id"] for old_module, _, _ in matched}
    return {
        "matched": matched,
        "added": [module for module in new_modules if module["id"] not in used_new],
        "removed": [module for module in old_modules if module["id"] not in matched_old_ids],
    }


def module_rename_map(module_match: dict | None) -> dict[str, str]:
    if not module_match:
        return {}
    return {
        old_module["id"]: new_module["id"]
        for old_module, new_module, _ in module_match.get("matched", [])
    }


def moved_file_entry(
    file_path: str,
    old_file: dict[str, Any],
    new_file: dict[str, Any],
    *,
    mod_rename: dict[str, str],
) -> dict[str, str] | None:
    old_mod = old_file.get("module", "")
    new_mod = new_file.get("module", "")
    normalized_old = mod_rename.get(old_mod, old_mod)
    if normalized_old == new_mod:
        return None
    return {"path": file_path, "old_module": old_mod, "new_module": new_mod}


def tag_change_entry(
    file_path: str,
    old_file: dict[str, Any],
    new_file: dict[str, Any],
) -> dict[str, Any] | None:
    old_tags = set(old_file.get("tags", []))
    new_tags = set(new_file.get("tags", []))
    added_tags = sorted(new_tags - old_tags)
    removed_tags = sorted(old_tags - new_tags)
    if not (added_tags or removed_tags):
        return None
    return {"path": file_path, "added": added_tags, "removed": removed_tags}


def diff_files(old_index: dict, new_index: dict, module_match: dict | None = None) -> dict[str, Any]:
    old_files = old_index.get("files", {})
    new_files = new_index.get("files", {})
    mod_rename = module_rename_map(module_match)

    old_paths = set(old_files)
    new_paths = set(new_files)
    files_moved = []
    files_tag_changed = []
    for file_path in sorted(old_paths & new_paths):
        old_file = old_files[file_path]
        new_file = new_files[file_path]
        moved = moved_file_entry(file_path, old_file, new_file, mod_rename=mod_rename)
        if moved:
            files_moved.append(moved)
        tag_change = tag_change_entry(file_path, old_file, new_file)
        if tag_change:
            files_tag_changed.append(tag_change)

    return {
        "files_added": sorted(new_paths - old_paths),
        "files_removed": sorted(old_paths - new_paths),
        "files_moved": files_moved,
        "files_tag_changed": files_tag_changed,
    }
