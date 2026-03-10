"""Public support helpers exposed for downstream integrations."""

from __future__ import annotations

from pathlib import Path

from .context_summary import summarize_architect_report, summarize_index
from .mcp.tools import navigate_tool
from .nav.context_pack import deduplicate_context, render_snippets
from .parsers.lang_map import filename_to_lang
from .parsers.query_loader import find_queries_dir
from .parsers.ts_extract import extract_definitions
from .tools.sig_extract import _infer_parent
from .utils import is_hidden


def summarize_project_index(index: dict, *, tier: str, max_tokens: int) -> str:
    return summarize_index(index, tier=tier, max_tokens=max_tokens)


def summarize_project_report(report: dict) -> str:
    return summarize_architect_report(report)


def navigate_context_pack(
    query: str,
    *,
    project_root: str | Path,
    focus_files: list[str] | None = None,
    budget_tokens: int = 5000,
) -> dict:
    return navigate_tool(
        query=query,
        focus_files=focus_files,
        budget_tokens=budget_tokens,
        hippo_dir=Path(project_root).resolve() / ".hippocampus",
    )


def render_deduplicated_overview(context_snippets: list[dict], static_overview: str) -> str:
    return deduplicate_context(context_snippets, static_overview)


def render_context_snippets(context_snippets: list[dict]) -> str:
    return render_snippets(context_snippets)


def language_for_file(file_path: str | Path) -> str | None:
    return filename_to_lang(str(file_path))


def resolve_queries_dir(project_root: str | Path) -> Path | None:
    return find_queries_dir(Path(project_root))


def extract_file_definitions(file_path: str | Path, rel_path: str, queries_dir: Path):
    return extract_definitions(str(file_path), rel_path, queries_dir)


def infer_parent_definition(definitions, definition):
    return _infer_parent(definitions, definition)


def is_hidden_path(path: str | Path) -> bool:
    return is_hidden(Path(path))
