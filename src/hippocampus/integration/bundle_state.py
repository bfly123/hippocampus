from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import (
    BUNDLE_STATE_FILE,
    CODE_SIGNATURES_FILE,
    FILE_MANIFEST_FILE,
    HIPPO_DIR,
    INDEX_FILE,
)
from ..utils import read_json, write_json

_FINGERPRINT_FILES = (
    INDEX_FILE,
    CODE_SIGNATURES_FILE,
    FILE_MANIFEST_FILE,
)


def _hippo_output_dir(project_root: str | Path) -> Path:
    root = Path(project_root).resolve()
    return root / HIPPO_DIR


def compute_bundle_fingerprint(project_root: str | Path) -> str:
    output_dir = _hippo_output_dir(project_root)
    hasher = hashlib.sha256()
    included = 0
    for name in _FINGERPRINT_FILES:
        path = output_dir / name
        if not path.exists() or not path.is_file():
            continue
        hasher.update(name.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
        included += 1
    if included <= 0:
        return ""
    return hasher.hexdigest()


def _file_count(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    files = payload.get("files", {})
    if not isinstance(files, dict):
        return 0
    return len(files)


def build_bundle_state(project_root: str | Path) -> dict[str, Any]:
    output_dir = _hippo_output_dir(project_root)
    index = read_json(output_dir / INDEX_FILE)
    manifest = read_json(output_dir / FILE_MANIFEST_FILE)
    signatures = read_json(output_dir / CODE_SIGNATURES_FILE)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle_fingerprint": compute_bundle_fingerprint(project_root),
        "index_file_count": _file_count(index),
        "manifest_file_count": _file_count(manifest),
        "signature_file_count": _file_count(signatures),
    }


def write_bundle_state(project_root: str | Path) -> Path:
    output_dir = _hippo_output_dir(project_root)
    out_path = output_dir / BUNDLE_STATE_FILE
    write_json(out_path, build_bundle_state(project_root))
    return out_path


__all__ = [
    "build_bundle_state",
    "compute_bundle_fingerprint",
    "write_bundle_state",
]
