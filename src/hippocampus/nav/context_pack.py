"""Context packing utilities for building LLM context."""

from typing import List, Dict, Any


def deduplicate_context(context_snippets: List[Dict[str, Any]], static_overview: str) -> str:
    """Remove files from static overview that are already in snippets.

    Args:
        context_snippets: List of FileSnippets dicts from navigate_tool
        static_overview: Static structure overview content (markdown)

    Returns:
        Filtered static overview with snippet files removed
    """
    # Extract file paths from snippets
    snippet_files = {s["file"] for s in context_snippets}

    if not snippet_files:
        return static_overview

    # Parse static overview and filter out lines containing snippet files
    # Use path-aware matching: look for markdown headers or exact file path tokens
    lines = static_overview.split('\n')
    filtered_lines = []

    for line in lines:
        # Check if this line is a markdown header containing a snippet file path
        # Pattern: ## path/to/file.py or ### path/to/file.py
        is_file_header = False
        if line.strip().startswith('#'):
            # Extract potential file path from header
            header_content = line.lstrip('#').strip()
            # Check if any snippet file path matches exactly
            for snippet_file in snippet_files:
                # Exact match or match at word boundary
                if snippet_file == header_content or f" {snippet_file}" in line or f"/{snippet_file}" in line:
                    is_file_header = True
                    break

        if not is_file_header:
            filtered_lines.append(line)

    return '\n'.join(filtered_lines)


def render_snippets(context_snippets: List[Dict[str, Any]]) -> str:
    """Render code snippets as markdown.

    Args:
        context_snippets: List of FileSnippets dicts

    Returns:
        Markdown-formatted snippet content
    """
    if not context_snippets:
        return ""

    sections = []
    for file_info in context_snippets:
        file_path = file_info["file"]
        rank = file_info["rank"]
        snippets = file_info["snippets"]

        sections.append(f"### {file_path} (rank: {rank:.3f})")

        for snippet in snippets:
            symbols = ", ".join(snippet["symbols"])
            content = snippet["content"]
            tokens = snippet["tokens"]

            sections.append(f"\n**Symbols**: {symbols} ({tokens} tokens)\n")
            sections.append("```")
            sections.append(content)
            sections.append("```\n")

    return "\n".join(sections)
