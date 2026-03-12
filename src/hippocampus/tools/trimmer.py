"""Dynamic trimmer that fits repomix output into a token budget."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..utils import estimate_tokens, write_json
from .trimmer_support import (
    build_candidates,
    build_ranker,
    filter_meaningful_files,
    load_compress_data,
    select_ranked_files,
)


def _group_files_by_dir(files: dict[str, str]) -> dict[str, list[tuple[str, str]]]:
    """Group file paths by their parent directory."""
    groups: dict[str, list[tuple[str, str]]] = {}
    for file_path, content in files.items():
        parts = file_path.split("/")
        dir_key = parts[0] if len(parts) > 1 else "."
        groups.setdefault(dir_key, []).append((file_path, content))
    return groups


def _dir_line_count(files: list[tuple[str, str]]) -> int:
    """Count total lines in a directory's files."""
    return sum(content.count("\n") + 1 for _, content in files)


def trim_compress(
    compress_data: dict,
    budget: int,
) -> dict[str, str]:
    """Trim compress output to fit within token budget."""
    files_data = compress_data.get("files", {})
    if not files_data:
        return {}

    sorted_dirs = sorted(
        _group_files_by_dir(files_data).items(),
        key=lambda item: _dir_line_count(item[1]),
        reverse=True,
    )
    result: dict[str, str] = {}
    remaining = budget
    for _dir_name, dir_files in sorted_dirs:
        if remaining <= 0:
            break
        for file_path, content in dir_files:
            cost = estimate_tokens(content)
            if cost > remaining:
                continue
            result[file_path] = content
            remaining -= cost
    return result


def trim_compress_with_ranker(
    compress_data: dict,
    budget: int,
    repo_root: Path,
    ranker,
    focus_files: list[str] | None = None,
    mentioned_files: set[str] | None = None,
    verbose: bool = False,
) -> dict:
    """Trim using a FileRanker strategy."""
    del repo_root, verbose
    files_data = compress_data.get("files", {})
    if not files_data:
        return {"files": {}, "metadata": {"error": "No files"}}

    filtered_files = filter_meaningful_files(files_data)
    ranked = ranker.rank_files(
        list(filtered_files.keys()),
        focus_files=focus_files,
        mentioned_files=mentioned_files,
    )
    result, remaining, selection_details = select_ranked_files(
        build_candidates(ranked, filtered_files),
        budget=budget,
    )
    return {
        "files": result,
        "metadata": {
            "selected_count": len(result),
            "total_tokens": budget - remaining,
            "remaining_budget": remaining,
            "ranking_method": ranker.__class__.__name__,
            "selection_details": selection_details,
        },
    }


def run_trimmer(
    target: Path,
    output_dir: Path,
    budget: int = 10000,
    compress_data: dict | None = None,
    ranking_method: str = "graph",
    focus_files: list[str] | None = None,
    mentioned_files: set[str] | None = None,
    verbose: bool = False,
) -> dict[str, str]:
    """Run the trimmer on repomix compress output."""
    if compress_data is None:
        compress_data = load_compress_data(target)

    trimmed_data = trim_compress_with_ranker(
        compress_data,
        budget,
        repo_root=target,
        ranker=build_ranker(target, ranking_method, verbose=verbose),
        focus_files=focus_files,
        mentioned_files=mentioned_files,
        verbose=verbose,
    )

    from ..constants import TRIMMED_FILE

    out_path = output_dir / TRIMMED_FILE
    write_json(
        out_path,
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "budget": budget,
            "file_count": len(trimmed_data["files"]),
            "files": trimmed_data["files"],
            **trimmed_data["metadata"],
        },
    )
    return trimmed_data["files"]
