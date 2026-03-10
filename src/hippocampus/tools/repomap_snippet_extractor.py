from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from ..utils import estimate_tokens


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
    file_tags = defaultdict(list)
    for tag in ranked_tags:
        if len(tag) == 5:
            rel_fname, _fname, line, name, kind = tag
            file_tags[rel_fname].append((line, name, kind))
        elif len(tag) == 1:
            continue
        else:
            continue

    result = []
    total_tokens_used = 0

    for file_path, rank in ranked_files:
        if total_tokens_used >= global_token_budget:
            break

        tags = file_tags.get(file_path, [])
        if not tags:
            continue

        mentioned_set = mentioned_idents or set()
        if mentioned_set:
            mentioned_lower = {s.lower() for s in mentioned_set}

            def tag_priority(tag):
                line, name, _kind = tag
                is_mentioned = name.lower() in mentioned_lower
                return (not is_mentioned, line)

            tags = sorted(tags, key=tag_priority)

        top_tags = tags[:max_snippets_per_file]

        file_snippets = []
        file_total_tokens = 0

        for line, name, _kind in top_tags:
            if total_tokens_used >= global_token_budget:
                break

            lois = list(range(max(1, line - 2), line + 10))

            abs_fname = str(root / file_path)
            rel_fname = file_path

            try:
                content = repomap.render_tree(abs_fname, rel_fname, lois)

                if not content or not content.strip():
                    continue

                tokens = estimate_tokens(content)

                if tokens > per_snippet_token_cap:
                    lines = content.split("\n")
                    truncated_lines = []
                    truncated_tokens = 0
                    for raw_line in lines:
                        line_tokens = estimate_tokens(raw_line)
                        if truncated_tokens + line_tokens > per_snippet_token_cap:
                            break
                        truncated_lines.append(raw_line)
                        truncated_tokens += line_tokens
                    content = "\n".join(truncated_lines)
                    tokens = truncated_tokens

                if total_tokens_used + tokens > global_token_budget:
                    break

                actual_lois = lois

                file_snippets.append(
                    {
                        "lois": actual_lois,
                        "symbols": [name],
                        "content": content,
                        "tokens": tokens,
                    }
                )

                file_total_tokens += tokens
                total_tokens_used += tokens

            except Exception as exc:
                if verbose:
                    print(
                        f"Warning: Failed to render snippet for {file_path}:{line} - {exc}"
                    )
                continue

        if file_snippets:
            result.append(
                {
                    "file": file_path,
                    "rank": rank,
                    "snippets": file_snippets,
                    "total_tokens": file_total_tokens,
                }
            )

    return result


__all__ = ["extract_ranked_snippets"]
