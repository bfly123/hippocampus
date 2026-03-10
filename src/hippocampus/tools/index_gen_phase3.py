"""Phase 3 enrichment helpers."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any


async def phase3a_enrich_module_impl(
    llm: Any,
    mod: dict,
    mod_files: list[str],
    phase1_results: dict[str, dict],
    *,
    project_root: Path | None = None,
) -> dict:
    """Run Phase 3a LLM call for a single module."""
    from ..llm.prompts import build_phase_3a_messages
    from ..llm.validators import _try_parse_json, validate_phase_3a

    mid = mod["id"]
    valid_files = set(mod_files)

    file_lines = []
    for fp in mod_files:
        desc = phase1_results.get(fp, {}).get("desc", "")
        file_lines.append(f"  {fp}: {desc}")
    module_files_text = "\n".join(file_lines)

    msg_3a = build_phase_3a_messages(
        project_root=project_root,
        module_id=mid,
        module_desc=mod.get("desc", ""),
        module_files=module_files_text[:3000],
    )

    def validator_3a(text):
        return validate_phase_3a(text, valid_files)

    text_3a, _ = await llm.call_with_retry("phase_3a", msg_3a, validator_3a)
    data_3a, _ = _try_parse_json(text_3a)

    enriched = dict(mod)
    enriched["file_count"] = len(mod_files)
    if data_3a:
        enriched["desc"] = data_3a.get("desc", mod.get("desc", ""))
        key_files = data_3a.get("key_files", [])
        enriched["key_files"] = [f for f in key_files if f in valid_files]
    return enriched


def infer_primary_lang_from_phase1(phase1_results: dict[str, dict]) -> str:
    lang_counter = Counter()
    for _fp, data in phase1_results.items():
        tags = data.get("tags", [])
        for tag in tags:
            if tag in (
                "python",
                "javascript",
                "typescript",
                "go",
                "rust",
                "java",
                "ruby",
                "c",
                "cpp",
            ):
                lang_counter[tag] += 1
    return lang_counter.most_common(1)[0][0] if lang_counter else "unknown"


def read_readme_excerpt(target: Path) -> str:
    for name in ("README.md", "README_zh.md"):
        path = target / name
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")[:500]
    return ""


async def build_project_overview_impl(
    llm: Any,
    enriched_modules: list[dict],
    phase1_results: dict[str, dict],
    target: Path,
) -> dict:
    """Run Phase 3b LLM call for project overview."""
    from ..llm.prompts import build_phase_3b_messages
    from ..llm.validators import _try_parse_json, validate_phase_3b

    module_summaries = "\n".join(
        f"- {m['id']}: {m.get('desc', '')}" for m in enriched_modules
    )
    readme_excerpt = read_readme_excerpt(target)
    primary_lang = infer_primary_lang_from_phase1(phase1_results)

    msg_3b = build_phase_3b_messages(
        project_root=target,
        module_summaries=module_summaries[:4000],
        readme_excerpt=readme_excerpt,
        file_count=len(phase1_results),
        module_count=len(enriched_modules),
        primary_lang=primary_lang,
    )

    text_3b, _ = await llm.call_with_retry("phase_3b", msg_3b, validate_phase_3b)
    project_data, _ = _try_parse_json(text_3b)
    return project_data if project_data else {
        "overview": "",
        "architecture": "",
        "scale": {
            "files": len(phase1_results),
            "modules": len(enriched_modules),
            "primary_lang": primary_lang,
        },
    }
