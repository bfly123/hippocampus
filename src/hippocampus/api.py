"""Stable import-facing API for hippocampus."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

from .api_support import (
    extract_file_definitions,
    infer_parent_definition,
    is_hidden_path,
    language_for_file,
    navigate_context_pack,
    render_context_snippets,
    render_deduplicated_overview,
    resolve_queries_dir,
    summarize_project_index,
    summarize_project_report,
)
from .config import default_config_yaml, load_config
from .constants import CONFIG_FILE, HIPPO_DIR, QUERIES_DIR, VENDOR_QUERIES_REL
from .nav import navigate as navigate_codebase
from .resources import copy_packaged_queries
from .tools.index_gen import run_index_pipeline
from .tools.sig_extract import run_sig_extract
from .tools.structure_prompt import run_structure_prompt
from .tools.tree_diff import run_tree_diff
from .tools.tree_gen import run_tree_gen


def _resolve_target(target: str | Path) -> tuple[Path, Path]:
    project_root = Path(target).resolve()
    output_dir = project_root / HIPPO_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    return project_root, output_dir


def initialize_project(target: str | Path = ".") -> Path:
    project_root = Path(target).resolve()
    output_dir = project_root / HIPPO_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    config_file = output_dir / CONFIG_FILE
    if not config_file.exists():
        config_file.write_text(default_config_yaml(), encoding="utf-8")

    queries_dir = output_dir / QUERIES_DIR
    queries_dir.mkdir(parents=True, exist_ok=True)

    vendor_src = project_root / VENDOR_QUERIES_REL
    if not vendor_src.exists():
        vendor_src = Path(__file__).resolve().parents[2] / VENDOR_QUERIES_REL
    if vendor_src.exists():
        for scm in vendor_src.glob("*.scm"):
            dst = queries_dir / scm.name
            if not dst.exists():
                shutil.copy2(scm, dst)
    else:
        copy_packaged_queries(queries_dir)
    return output_dir


def extract_signatures(target: str | Path = ".", *, verbose: bool = False):
    project_root, output_dir = _resolve_target(target)
    return run_sig_extract(project_root, output_dir, verbose=verbose)


def build_tree(target: str | Path = ".", *, verbose: bool = False):
    project_root, output_dir = _resolve_target(target)
    return run_tree_gen(project_root, output_dir, verbose=verbose)


def build_tree_diff(target: str | Path = ".", *, verbose: bool = False):
    _, output_dir = _resolve_target(target)
    return run_tree_diff(output_dir, verbose=verbose)


def build_index(target: str | Path = ".", *, verbose: bool = False, no_llm: bool = False) -> dict[str, Any]:
    project_root, output_dir = _resolve_target(target)
    config_path = output_dir / CONFIG_FILE
    config = load_config(config_path if config_path.exists() else None, project_root=project_root)
    return asyncio.run(
        run_index_pipeline(project_root, output_dir, config, verbose=verbose, no_llm=no_llm)
    )


def generate_structure_prompt(
    target: str | Path = ".",
    *,
    max_tokens: int = 4000,
    profile: str = "auto",
    llm_enhance: bool | None = None,
) -> str:
    _, output_dir = _resolve_target(target)
    config_path = output_dir / CONFIG_FILE
    config = load_config(config_path if config_path.exists() else None, project_root=Path(target).resolve())
    return run_structure_prompt(
        output_dir,
        max_tokens=max_tokens,
        config=config,
        llm_enhance=config.structure_prompt_llm_enhance if llm_enhance is None else llm_enhance,
        render_profile=profile,
    )


def navigate(
    query: str,
    *,
    focus_files: list[str] | None = None,
    conversation_files: list[str] | None = None,
    budget_tokens: int = 5000,
    target: str | Path = ".",
):
    return navigate_codebase(
        query=query,
        focus_files=focus_files,
        conversation_files=conversation_files,
        budget_tokens=budget_tokens,
        hippo_dir=Path(target).resolve() / HIPPO_DIR,
    )


__all__ = [
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
