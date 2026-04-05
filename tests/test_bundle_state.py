from __future__ import annotations

import json

from hippocampus.integration.bundle_state import (
    compute_bundle_fingerprint,
    write_bundle_state,
)


def _write_bundle_files(tmp_path, *, manifest_kind: str = "source") -> None:
    hippo = tmp_path / ".hippocampus"
    hippo.mkdir(parents=True, exist_ok=True)
    (hippo / "hippocampus-index.json").write_text(
        '{"files":{"src/app.py":{}}}\n',
        encoding="utf-8",
    )
    (hippo / "code-signatures.json").write_text(
        '{"files":{"src/app.py":{"signatures":[]}}}\n',
        encoding="utf-8",
    )
    (hippo / "file-manifest.json").write_text(
        json.dumps({"files": {"src/app.py": {"kind": manifest_kind}}}) + "\n",
        encoding="utf-8",
    )


def test_write_bundle_state_emits_expected_metadata(tmp_path):
    _write_bundle_files(tmp_path)

    out_path = write_bundle_state(tmp_path)
    payload = json.loads(out_path.read_text(encoding="utf-8"))

    assert out_path.name == "bundle-state.json"
    assert payload["bundle_fingerprint"] == compute_bundle_fingerprint(tmp_path)
    assert payload["index_file_count"] == 1
    assert payload["manifest_file_count"] == 1
    assert payload["signature_file_count"] == 1
    assert payload["generated_at"]


def test_bundle_fingerprint_changes_when_bundle_files_change(tmp_path):
    _write_bundle_files(tmp_path, manifest_kind="source")
    before = compute_bundle_fingerprint(tmp_path)

    _write_bundle_files(tmp_path, manifest_kind="config")
    after = compute_bundle_fingerprint(tmp_path)

    assert before
    assert after
    assert before != after
