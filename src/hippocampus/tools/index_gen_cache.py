from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..constants import PHASE1_CACHE_FILE, PHASE2_CACHE_FILE, PHASE3_CACHE_FILE
from ..utils import read_json, write_json


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_phase1_cache(output_dir: Path) -> dict[str, Any]:
    cache_path = output_dir / PHASE1_CACHE_FILE
    return read_json(cache_path) if cache_path.exists() else {}


def save_phase1_cache(output_dir: Path, cache: dict[str, Any]) -> None:
    write_json(output_dir / PHASE1_CACHE_FILE, cache)


def phase2_input_hash(phase1_results: dict[str, dict]) -> str:
    parts: list[str] = []
    for file_path in sorted(phase1_results):
        data = phase1_results[file_path]
        desc = data.get("desc", "")
        tags = ",".join(sorted(data.get("tags", [])))
        parts.append(f"{file_path}|{desc}|{tags}")
    return content_hash("\n".join(parts))


def load_phase2_cache(output_dir: Path) -> dict[str, Any]:
    cache_path = output_dir / PHASE2_CACHE_FILE
    return read_json(cache_path) if cache_path.exists() else {}


def save_phase2_cache(output_dir: Path, cache: dict[str, Any]) -> None:
    write_json(output_dir / PHASE2_CACHE_FILE, cache)


def phase3_module_input_hash(
    module_id: str,
    module_desc: str,
    member_files: list[str],
    phase1_results: dict[str, dict],
) -> str:
    parts = [f"{module_id}|{module_desc}"]
    for file_path in sorted(member_files):
        desc = phase1_results.get(file_path, {}).get("desc", "")
        parts.append(f"{file_path}|{desc}")
    return content_hash("\n".join(parts))


def load_phase3_cache(output_dir: Path) -> dict[str, Any]:
    cache_path = output_dir / PHASE3_CACHE_FILE
    return read_json(cache_path) if cache_path.exists() else {}


def save_phase3_cache(output_dir: Path, cache: dict[str, Any]) -> None:
    write_json(output_dir / PHASE3_CACHE_FILE, cache)
