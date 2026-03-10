"""Code signature extractor — extracts definitions via tree-sitter."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..parsers.lang_map import filename_to_lang
from ..parsers.query_loader import find_queries_dir
from ..parsers.ts_extract import extract_definitions
from ..types import CodeSignaturesDoc, FileSignatures, Signature
from ..utils import is_hidden, write_json


def _collect_source_files(target: Path) -> list[Path]:
    """Collect all source files under target, skipping hidden dirs and vendor."""
    files = []
    for p in sorted(target.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(target)
        if is_hidden(rel):
            continue
        if rel.parts and rel.parts[0] == "vendor":
            continue
        if filename_to_lang(str(p)) is not None:
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


def run_sig_extract(
    target: Path,
    output_dir: Path,
    verbose: bool = False,
) -> CodeSignaturesDoc:
    """Extract code signatures from all source files under target."""
    queries_dir = find_queries_dir(target)
    if queries_dir is None:
        # Fallback: try output_dir parent
        from ..constants import HIPPO_DIR, QUERIES_DIR
        queries_dir = target / HIPPO_DIR / QUERIES_DIR
        if not queries_dir.is_dir():
            raise FileNotFoundError(
                f"Queries directory not found. Run 'hippo init' first."
            )

    source_files = _collect_source_files(target)
    doc = CodeSignaturesDoc(
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    for fpath in source_files:
        rel = str(fpath.relative_to(target))
        lang = filename_to_lang(str(fpath))
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

    # Write output
    from ..constants import CODE_SIGNATURES_FILE
    out_path = output_dir / CODE_SIGNATURES_FILE
    write_json(out_path, doc.model_dump())

    return doc
