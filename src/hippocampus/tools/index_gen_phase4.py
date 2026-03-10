from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def phase_4_merge_impl(
    phase0_data: dict[str, Any],
    phase1_results: dict[str, dict],
    modules: list[dict],
    file_to_module: dict[str, str],
    project_node: dict,
    compute_module_dependencies_fn: Callable[
        [dict[str, dict], dict[str, str], Path],
        tuple[dict[str, list[dict[str, Any]]], dict[str, list[str]]],
    ],
    compute_function_dependencies_fn: Callable[
        [dict[str, dict], Path], dict[str, list[dict[str, Any]]]
    ],
    target: Path | None = None,
) -> dict:
    sig_doc = phase0_data["signatures"]

    files_index: dict[str, dict] = {}
    for fpath, p1 in phase1_results.items():
        file_sigs = sig_doc.files.get(fpath)
        sigs_out = []
        if file_sigs:
            p1_sigs = p1.get("signatures", [])
            for i, s in enumerate(file_sigs.signatures):
                entry = {
                    "name": s.name,
                    "kind": s.kind,
                    "line": s.line,
                }
                if s.parent:
                    entry["parent"] = s.parent
                if i < len(p1_sigs):
                    entry["desc"] = p1_sigs[i].get("desc", "")
                sigs_out.append(entry)

        files_index[fpath] = {
            "id": f"file:{fpath}",
            "type": "file",
            "name": fpath.split("/")[-1],
            "lang": file_sigs.lang if file_sigs else "unknown",
            "desc": p1.get("desc", ""),
            "tags": p1.get("tags", []),
            "module": file_to_module.get(fpath, ""),
            "signatures": sigs_out,
        }

    index = {
        "version": 2,
        "schema": "hippocampus-index/v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": project_node,
        "modules": modules,
        "files": files_index,
        "stats": {
            "total_files": len(files_index),
            "total_modules": len(modules),
            "total_signatures": sum(
                len(f["signatures"]) for f in files_index.values()
            ),
        },
    }

    from ..scoring import compute_module_scores

    compute_module_scores(index)

    if target:
        module_dependencies, file_dependencies = compute_module_dependencies_fn(
            files_index, file_to_module, target
        )
        index["module_dependencies"] = module_dependencies
        index["file_dependencies"] = file_dependencies
        index["function_dependencies"] = compute_function_dependencies_fn(
            files_index, target
        )

    return index
