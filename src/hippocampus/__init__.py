"""Hippocampus — Code repository indexing and analysis toolkit."""

__version__ = "0.1.0"

from .api import (
    build_index,
    build_tree,
    build_tree_diff,
    extract_file_definitions,
    extract_signatures,
    generate_structure_prompt,
    infer_parent_definition,
    initialize_project,
    is_hidden_path,
    language_for_file,
    navigate,
    navigate_context_pack,
    render_context_snippets,
    render_deduplicated_overview,
    resolve_queries_dir,
    summarize_project_index,
    summarize_project_report,
)

__all__ = [
    "__version__",
    "build_index",
    "build_tree",
    "build_tree_diff",
    "extract_file_definitions",
    "extract_signatures",
    "generate_structure_prompt",
    "infer_parent_definition",
    "initialize_project",
    "is_hidden_path",
    "language_for_file",
    "navigate",
    "navigate_context_pack",
    "render_context_snippets",
    "render_deduplicated_overview",
    "resolve_queries_dir",
    "summarize_project_index",
    "summarize_project_report",
]
