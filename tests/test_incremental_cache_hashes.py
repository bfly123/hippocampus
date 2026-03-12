"""Tests for incremental cache hashing and persistence."""

from __future__ import annotations

from incremental_cache_helpers import (
    _load_phase2_cache,
    _load_phase3_cache,
    _phase2_input_hash,
    _phase3_module_input_hash,
    _save_phase2_cache,
    _save_phase3_cache,
    phase1_results,
)


class TestPhase2InputHash:
    def test_deterministic(self, phase1_results):
        assert _phase2_input_hash(phase1_results) == _phase2_input_hash(phase1_results)

    def test_changes_on_desc_change(self, phase1_results):
        h1 = _phase2_input_hash(phase1_results)
        phase1_results["src/main.py"]["desc"] = "Changed desc"
        assert h1 != _phase2_input_hash(phase1_results)

    def test_changes_on_file_add(self, phase1_results):
        h1 = _phase2_input_hash(phase1_results)
        phase1_results["src/new.py"] = {"desc": "New file", "tags": ["python"]}
        assert h1 != _phase2_input_hash(phase1_results)

    def test_changes_on_tag_change(self, phase1_results):
        h1 = _phase2_input_hash(phase1_results)
        phase1_results["src/main.py"]["tags"] = ["cli", "python", "new-tag"]
        assert h1 != _phase2_input_hash(phase1_results)


class TestPhase3ModuleInputHash:
    def test_deterministic(self, phase1_results):
        h1 = _phase3_module_input_hash(
            "mod:core",
            "Core logic",
            ["src/main.py", "src/utils.py"],
            phase1_results,
        )
        h2 = _phase3_module_input_hash(
            "mod:core",
            "Core logic",
            ["src/main.py", "src/utils.py"],
            phase1_results,
        )
        assert h1 == h2

    def test_changes_on_member_desc_change(self, phase1_results):
        h1 = _phase3_module_input_hash(
            "mod:core",
            "Core logic",
            ["src/main.py", "src/utils.py"],
            phase1_results,
        )
        phase1_results["src/main.py"]["desc"] = "Changed"
        h2 = _phase3_module_input_hash(
            "mod:core",
            "Core logic",
            ["src/main.py", "src/utils.py"],
            phase1_results,
        )
        assert h1 != h2

    def test_changes_on_member_list_change(self, phase1_results):
        h1 = _phase3_module_input_hash(
            "mod:core",
            "Core logic",
            ["src/main.py", "src/utils.py"],
            phase1_results,
        )
        h2 = _phase3_module_input_hash(
            "mod:core",
            "Core logic",
            ["src/main.py"],
            phase1_results,
        )
        assert h1 != h2


class TestCachePersistence:
    def test_phase2_cache_roundtrip(self, tmp_path):
        out = tmp_path / ".hippocampus"
        out.mkdir()
        data = {
            "input_hash": "abc123",
            "modules": [{"id": "mod:core", "desc": "Core"}],
            "file_to_module": {"src/main.py": "mod:core"},
            "file_hashes": {"src/main.py": "hash1"},
        }
        _save_phase2_cache(out, data)
        assert _load_phase2_cache(out) == data

    def test_phase2_cache_missing_returns_empty(self, tmp_path):
        out = tmp_path / ".hippocampus"
        out.mkdir()
        assert _load_phase2_cache(out) == {}

    def test_phase3_cache_roundtrip(self, tmp_path):
        out = tmp_path / ".hippocampus"
        out.mkdir()
        data = {
            "phase_3a": {
                "mod:core": {
                    "hash": "h1",
                    "result": {"desc": "Core logic", "key_files": ["a.py"]},
                }
            },
            "phase_3b": {
                "hash": "h2",
                "result": {
                    "overview": "A project",
                    "architecture": "modular",
                    "scale": {"files": 4, "modules": 2, "primary_lang": "python"},
                },
            },
        }
        _save_phase3_cache(out, data)
        assert _load_phase3_cache(out) == data

    def test_phase3_cache_missing_returns_empty(self, tmp_path):
        out = tmp_path / ".hippocampus"
        out.mkdir()
        assert _load_phase3_cache(out) == {}
