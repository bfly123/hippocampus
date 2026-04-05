"""Hippocampus — Code repository indexing and analysis toolkit."""

from __future__ import annotations

import sys
from importlib import import_module

__version__ = "0.1.7"

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

_LEGACY_MODULE_ALIASES = {
    "hippocampus.resource_paths": "hippocampus.integration.resource_paths",
    "hippocampus.api_support": "hippocampus.api.support",
    "hippocampus.cli_commands_core": "hippocampus.cli.commands_core",
    "hippocampus.cli_commands_pipeline": "hippocampus.cli.commands_pipeline",
    "hippocampus.cli_commands_project_bootstrap": "hippocampus.cli.commands_project_bootstrap",
    "hippocampus.cli_commands_structure_prompt": "hippocampus.cli.commands_structure_prompt",
    "hippocampus.cli_pipeline_command_builders": "hippocampus.cli.pipeline_command_builders",
    "hippocampus.cli_pipeline_helpers": "hippocampus.cli.pipeline_helpers",
    "hippocampus.cli_query": "hippocampus.cli.query",
    "hippocampus.cli_snapshot": "hippocampus.cli.snapshot",
}

for legacy_name, current_name in _LEGACY_MODULE_ALIASES.items():
    sys.modules.setdefault(legacy_name, import_module(current_name))
