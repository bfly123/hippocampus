"""Snapshot archival — save, list, load, and resolve index snapshots."""

from __future__ import annotations

import json
import logging
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ..constants import INDEX_FILE, SNAPSHOTS_DIR
from ..utils import read_json, write_json

log = logging.getLogger(__name__)


def save_snapshot(output_dir: Path, message: str | None = None) -> dict:
    """Archive current index as a timestamped snapshot.

    Returns dict with snapshot_id, path, and stats.
    """
    index_path = output_dir / INDEX_FILE
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}")

    index = read_json(index_path)

    now = datetime.now(timezone.utc)
    snapshot_id = now.strftime("%Y%m%dT%H%M%S_%fZ")

    snapshot_meta = {
        "snapshot_id": snapshot_id,
        "snapshot_created_at": now.isoformat(),
    }
    if message:
        snapshot_meta["message"] = message

    index["_snapshot"] = snapshot_meta

    snap_dir = output_dir / SNAPSHOTS_DIR
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_path = snap_dir / f"{snapshot_id}.json"

    # Atomic write: temp file + rename to prevent partial reads
    fd, tmp_path = tempfile.mkstemp(
        dir=str(snap_dir), suffix=".tmp", prefix=".snap_",
    )
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        Path(tmp_path).replace(snap_path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    return {
        "snapshot_id": snapshot_id,
        "path": str(snap_path),
        "stats": index.get("stats", {}),
    }


def list_snapshots(output_dir: Path) -> list[dict]:
    """List all snapshots in reverse chronological order.

    Returns list of dicts with snapshot_id, generated_at, message, stats.
    Only reads lightweight metadata — does not load full file lists.
    """
    snap_dir = output_dir / SNAPSHOTS_DIR
    if not snap_dir.exists():
        return []

    results = []
    for p in sorted(snap_dir.glob("*.json"), reverse=True):
        try:
            data = read_json(p)
        except (json.JSONDecodeError, OSError):
            log.warning("Skipping corrupted snapshot: %s", p)
            continue
        meta = data.get("_snapshot", {})
        entry = {
            "snapshot_id": meta.get("snapshot_id", p.stem),
            "generated_at": meta.get("snapshot_created_at", data.get("generated_at", "")),
            "message": meta.get("message", ""),
            "stats": data.get("stats", {}),
        }
        results.append(entry)

    return results


def load_snapshot(output_dir: Path, snapshot_id: str) -> dict:
    """Load a full snapshot by its ID.

    Raises FileNotFoundError if snapshot does not exist.
    """
    snap_path = output_dir / SNAPSHOTS_DIR / f"{snapshot_id}.json"
    if not snap_path.exists():
        raise FileNotFoundError(f"Snapshot not found: {snap_path}")
    return read_json(snap_path)


def resolve_snapshot(output_dir: Path, ref: str) -> dict:
    """Resolve a snapshot reference to a full index dict.

    Supported refs:
      - "current"     → current hippocampus-index.json (not archived)
      - "latest"      → most recent snapshot
      - "latest~N"    → Nth snapshot before latest (latest~1 = second newest)
      - exact ID      → e.g. "20260210T143000_123456Z"
    """
    if ref == "current":
        index_path = output_dir / INDEX_FILE
        if not index_path.exists():
            raise FileNotFoundError(f"Current index not found: {index_path}")
        return read_json(index_path)

    if ref == "latest" or ref.startswith("latest~"):
        snap_dir = output_dir / SNAPSHOTS_DIR
        if not snap_dir.exists():
            raise FileNotFoundError("No snapshots directory found.")

        snaps = sorted(snap_dir.glob("*.json"))
        if not snaps:
            raise FileNotFoundError("No snapshots found.")

        if ref == "latest":
            offset = 0
        else:
            m = re.match(r"^latest~(\d+)$", ref)
            if not m:
                raise ValueError(f"Invalid snapshot ref: {ref}")
            offset = int(m.group(1))

        idx = len(snaps) - 1 - offset
        if idx < 0:
            raise FileNotFoundError(
                f"Snapshot ref '{ref}' out of range "
                f"(only {len(snaps)} snapshots available)."
            )
        return read_json(snaps[idx])

    # Exact snapshot ID
    return load_snapshot(output_dir, ref)
