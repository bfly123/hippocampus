from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from ..utils import estimate_tokens


def _file_tags_by_path(ranked_tags: list[tuple]) -> dict[str, list[tuple[int, str, Any]]]:
    file_tags: dict[str, list[tuple[int, str, Any]]] = defaultdict(list)
    for tag in ranked_tags:
        if len(tag) == 5:
            rel_fname, _fname, line, name, kind = tag
            file_tags[rel_fname].append((line, name, kind))
    return file_tags


def _prioritized_tags(
    tags: list[tuple[int, str, Any]],
    mentioned_idents: set[str] | None,
) -> list[tuple[int, str, Any]]:
    mentioned_lower = {item.lower() for item in mentioned_idents or set()}

    def tag_priority(tag):
        line, name, _kind = tag
        is_private = name.startswith("_")
        is_mentioned = name.lower() in mentioned_lower
        return (not is_mentioned, is_private, line)

    return sorted(tags, key=tag_priority)


def _truncate_snippet(content: str, *, per_snippet_token_cap: int) -> tuple[str, int]:
    tokens = estimate_tokens(content)
    if tokens <= per_snippet_token_cap:
        return content, tokens

    truncated_lines: list[str] = []
    truncated_tokens = 0
    for raw_line in content.split("\n"):
        line_tokens = estimate_tokens(raw_line)
        if truncated_tokens + line_tokens > per_snippet_token_cap:
            break
        truncated_lines.append(raw_line)
        truncated_tokens += line_tokens
    return "\n".join(truncated_lines), truncated_tokens


def _render_snippet(
    *,
    repomap,
    root: Path,
    file_path: str,
    line: int,
    name: str,
    per_snippet_token_cap: int,
) -> dict[str, Any] | None:
    lois = list(range(max(1, line - 2), line + 10))
    content = repomap.render_tree(str(root / file_path), file_path, lois)
    if not content or not content.strip():
        return None

    content, tokens = _truncate_snippet(content, per_snippet_token_cap=per_snippet_token_cap)
    return {
        "lois": lois,
        "symbols": [name],
        "content": content,
        "tokens": tokens,
    }


def _append_file_result(
    result: list[dict[str, Any]],
    *,
    file_path: str,
    rank: float,
    file_snippets: list[dict[str, Any]],
    file_total_tokens: int,
) -> None:
    if file_snippets:
        result.append(
            {
                "file": file_path,
                "rank": rank,
                "snippets": file_snippets,
                "total_tokens": file_total_tokens,
            }
        )


def extract_ranked_snippets(
    *,
    repomap,
    root: Path,
    verbose: bool,
    ranked_tags: list[tuple],
    ranked_files: list[tuple[str, float]],
    max_snippets_per_file: int = 2,
    global_token_budget: int = 2500,
    per_snippet_token_cap: int = 500,
    mentioned_idents: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Extract code snippets from ranked RepoMap tags."""
    file_tags = _file_tags_by_path(ranked_tags)
    result: list[dict[str, Any]] = []
    total_tokens_used = 0

    for file_path, rank in ranked_files:
        if total_tokens_used >= global_token_budget:
            break
        tags = _prioritized_tags(file_tags.get(file_path, []), mentioned_idents)
        if not tags:
            continue

        file_snippets: list[dict[str, Any]] = []
        file_total_tokens = 0
        for line, name, _kind in tags[:max_snippets_per_file]:
            if total_tokens_used >= global_token_budget:
                break
            try:
                snippet = _render_snippet(
                    repomap=repomap,
                    root=root,
                    file_path=file_path,
                    line=line,
                    name=name,
                    per_snippet_token_cap=per_snippet_token_cap,
                )
            except Exception as exc:
                if verbose:
                    print(f"Warning: Failed to render snippet for {file_path}:{line} - {exc}")
                continue
            if not snippet:
                continue
            if total_tokens_used + snippet["tokens"] > global_token_budget:
                break
            file_snippets.append(snippet)
            file_total_tokens += snippet["tokens"]
            total_tokens_used += snippet["tokens"]

        _append_file_result(
            result,
            file_path=file_path,
            rank=rank,
            file_snippets=file_snippets,
            file_total_tokens=file_total_tokens,
        )

    return result


__all__ = ["extract_ranked_snippets"]
