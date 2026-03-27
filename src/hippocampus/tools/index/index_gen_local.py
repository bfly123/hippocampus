"""Local-only helpers for index generation."""

from __future__ import annotations

import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from ...source_filter import build_file_manifest, should_include_architecture_file, write_file_manifest


def get_git_changed_files(target: Path) -> set[str] | None:
    """Get changed files from git diff. Returns None if not a git repo or on error."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=target,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            changed = {line.strip() for line in result.stdout.strip().split("\n") if line.strip()}
            return changed if changed else set()
    except Exception:
        pass
    return None


def detect_lang_hint(target: Path) -> str:
    """Detect project language for desc output."""
    readme = target / "README.md"
    if not readme.exists():
        readme = target / "README_zh.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="replace")[:500]
        cn_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        if cn_chars / max(len(text), 1) > 0.3:
            return "中文"
    return "英文"


def build_local_phase1_results(
    phase0_data: dict[str, Any],
    target: Path,
) -> dict[str, dict]:
    """Build minimal phase1-style results without LLM calls."""
    del target
    sig_doc = phase0_data["signatures"]
    compress = phase0_data["compress"]

    files = set(compress.get("files", {}).keys()) | set(sig_doc.files.keys())
    results: dict[str, dict] = {}
    for fp in files:
        if not should_include_architecture_file(fp):
            continue
        results[fp] = {
            "desc": "",
            "tags": [],
            "signatures": [],
        }
    return results


def infer_primary_lang_from_signatures(
    phase0_data: dict[str, Any],
    phase1_results: dict[str, dict],
) -> str:
    """Infer primary language from signature metadata."""
    sig_doc = phase0_data["signatures"]
    counter: Counter[str] = Counter()
    for fp in phase1_results:
        file_sigs = sig_doc.files.get(fp)
        if file_sigs and file_sigs.lang:
            counter[file_sigs.lang] += 1
    return counter.most_common(1)[0][0] if counter else "unknown"


def build_local_only_index(
    phase0_data: dict[str, Any],
    target: Path,
    *,
    merge_fn: Callable[..., dict],
) -> dict:
    """Build a minimal index without LLM phases, preserving existing output shape."""
    phase1_results = build_local_phase1_results(phase0_data, target)
    primary_lang = infer_primary_lang_from_signatures(
        phase0_data, phase1_results
    )
    project_node = {
        "overview": "",
        "architecture": "",
        "scale": {
            "files": len(phase1_results),
            "modules": 0,
            "primary_lang": primary_lang,
        },
    }
    return merge_fn(
        phase0_data,
        phase1_results,
        [],
        {},
        project_node,
        target=target,
    )


async def phase_0_local(
    target: Path,
    output_dir: Path,
    verbose: bool = False,
) -> dict[str, Any]:
    """Phase 0: local extraction without LLM."""
    from ..sig_extract import run_sig_extract
    from ...repomix.runner import run_repomix_compress

    git_changed_files = get_git_changed_files(target)
    if verbose and git_changed_files is not None:
        print(f"Git diff detected: {len(git_changed_files)} changed files")

    sig_doc = run_sig_extract(target, output_dir, verbose=verbose)
    file_manifest = build_file_manifest(target)
    write_file_manifest(output_dir, file_manifest)

    with tempfile.NamedTemporaryFile(
        suffix=".json",
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        compress_data = run_repomix_compress(target, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "signatures": sig_doc,
        "compress": compress_data,
        "file_manifest": file_manifest,
        "git_changed_files": git_changed_files,
    }
