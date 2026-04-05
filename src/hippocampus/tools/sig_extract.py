"""Code signature extractor — extracts definitions via tree-sitter."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..architecture_rules import load_hippo_rules
from ..parsers.lang_map import detect_file_language
from ..parsers.query_loader import find_queries_dir
from ..parsers.ts_extract import extract_definitions
from ..resources import packaged_queries_dir
from ..source_filter import classify_project_file
from ..types import CodeSignaturesDoc, FileSignatures, Signature
from ..utils import write_json


def _collect_source_files(target: Path) -> list[Path]:
    """Collect architecture source files under target."""
    rules = load_hippo_rules(target)
    files = []
    for p in sorted(target.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(target)
        classified = classify_project_file(rel, rules=rules, project_root=target)
        if classified.include_in_architecture and classified.language is not None:
            files.append(p)
    return files


def _infer_parent(tags: list, current_tag) -> str | None:
    """Infer parent class/module for a method tag based on line proximity."""
    best = None
    for t in tags:
        if t.tag_type == "class" and t.line < current_tag.line:
            if best is None or t.line > best.line:
                best = t
    return best.name if best else None


def _extract_signatures_with_queries(
    *,
    target: Path,
    output_dir: Path,
    queries_dir: Path,
) -> CodeSignaturesDoc:
    source_files = _collect_source_files(target)
    doc = CodeSignaturesDoc(
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    for fpath in source_files:
        rel = str(fpath.relative_to(target))
        lang = detect_file_language(fpath)
        if not lang:
            continue

        defs = extract_definitions(str(fpath), rel, queries_dir)
        if not defs:
            continue

        sigs = []
        for d in defs:
            parent = None
            if d.tag_type in ("function", "method"):
                parent = _infer_parent(defs, d)
            kind = d.tag_type or "function"
            sigs.append(Signature(
                name=d.name,
                kind=kind,
                line=d.line,
                parent=parent,
            ))

        doc.files[rel] = FileSignatures(lang=lang, signatures=sigs)

    from ..constants import CODE_SIGNATURES_FILE
    out_path = output_dir / CODE_SIGNATURES_FILE
    write_json(out_path, doc.model_dump())

    return doc


def run_sig_extract(
    target: Path,
    output_dir: Path,
    verbose: bool = False,
) -> CodeSignaturesDoc:
    """Extract code signatures from all source files under target."""
    queries_dir = find_queries_dir(target)
    if queries_dir is not None:
        return _extract_signatures_with_queries(
            target=target,
            output_dir=output_dir,
            queries_dir=queries_dir,
        )

    from ..constants import HIPPO_DIR, QUERIES_DIR

    local_queries = target / HIPPO_DIR / QUERIES_DIR
    if local_queries.is_dir():
        return _extract_signatures_with_queries(
            target=target,
            output_dir=output_dir,
            queries_dir=local_queries,
        )

    with packaged_queries_dir() as packaged_dir:
        if packaged_dir.is_dir():
            return _extract_signatures_with_queries(
                target=target,
                output_dir=output_dir,
                queries_dir=packaged_dir,
            )

    raise FileNotFoundError(
        "Queries directory not found. Run 'hippo init' first."
    )
