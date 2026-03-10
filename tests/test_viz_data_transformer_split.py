from __future__ import annotations

import json

from hippocampus.viz import data_transformer as dt


def _sample_index() -> dict:
    return {
        "modules": [
            {"id": "mod:core", "role": "core", "core_score": 0.9, "file_count": 1}
        ],
        "files": {
            "src/a.py": {
                "id": "src/a.py",
                "name": "a.py",
                "module": "mod:core",
                "signatures": [{"name": "f"}],
                "lang": "python",
            }
        },
        "file_dependencies": {"src/a.py": []},
        "module_dependencies": {},
        "function_dependencies": {"src/a.py:f": []},
    }


def test_transformer_facade_exports_basic_transforms():
    index = _sample_index()

    modules_graph = dt.transform_modules_to_graph(index)
    assert "nodes" in modules_graph
    assert "links" in modules_graph
    assert "categories" in modules_graph

    files_graph = dt.transform_files_to_graph(index)
    assert "nodes" in files_graph
    assert "links" in files_graph

    funcs_graph = dt.transform_functions_to_graph(index)
    assert "nodes" in funcs_graph
    assert "links" in funcs_graph


def test_transformer_legacy_private_aliases_available():
    assert dt._get_tier_color("core")
    assert dt._get_role_color("core")
    assert isinstance(dt._ROLE_COLORS, dict)


def test_transform_snapshots_trends_and_frames(tmp_path):
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir(parents=True)

    payload = {
        "_snapshot": {
            "snapshot_id": "s1",
            "snapshot_created_at": "2026-03-07T09:00:00Z",
        },
        "modules": [{"id": "mod:core", "core_score": 0.8, "tier": "core", "role": "core"}],
        "module_dependencies": {},
        "files": [],
    }
    (snapshots / "20260307.json").write_text(json.dumps(payload), encoding="utf-8")

    trends = dt.transform_snapshots_to_trends(snapshots)
    assert trends["dates"] == ["20260307"]

    frames = dt.transform_snapshots_to_frames(snapshots)
    assert len(frames["frames"]) == 1
    assert frames["module_ids"] == ["mod:core"]
