"""HTML templates for visualization."""

from __future__ import annotations

from pathlib import Path


def _load_html_header() -> str:
    templates_dir = Path(__file__).resolve().parent.parent / "resources" / "templates"
    parts = sorted(templates_dir.glob("viz_part_*.html"))
    return "".join(part.read_text(encoding="utf-8") for part in parts)


HTML_HEADER = _load_html_header()


__all__ = ["HTML_HEADER"]
