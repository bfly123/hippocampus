"""Tests for Phase 2 and Phase 3 incremental caching."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hippocampus.tools.index_gen import (
    _content_hash,
    _phase2_input_hash,
    _phase3_module_input_hash,
    _load_phase2_cache,
    _save_phase2_cache,
    _load_phase3_cache,
    _save_phase3_cache,
    phase_2,
    phase_3,
)


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def phase1_results():
    """Minimal Phase 1 results for 4 files."""
    return {
        "src/main.py": {"desc": "Entry point", "tags": ["cli", "python"]},
        "src/utils.py": {"desc": "Utility helpers", "tags": ["utils", "python"]},
        "src/config.py": {"desc": "Config loader", "tags": ["config", "python"]},
        "src/server.py": {"desc": "HTTP server", "tags": ["http", "python"]},
    }


@pytest.fixture
def modules_list():
    """Sample module definitions."""
    return [
        {"id": "mod:core", "desc": "Core logic"},
        {"id": "mod:infra", "desc": "Infrastructure"},
    ]


@pytest.fixture
def file_to_module():
    """Sample file-to-module mapping."""
    return {
        "src/main.py": "mod:core",
        "src/utils.py": "mod:core",
        "src/config.py": "mod:infra",
        "src/server.py": "mod:infra",
    }


# ── Hash function tests ──────────────────────────────────────────


class TestPhase2InputHash:
    def test_deterministic(self, phase1_results):
        h1 = _phase2_input_hash(phase1_results)
        h2 = _phase2_input_hash(phase1_results)
        assert h1 == h2

    def test_changes_on_desc_change(self, phase1_results):
        h1 = _phase2_input_hash(phase1_results)
        phase1_results["src/main.py"]["desc"] = "Changed desc"
        h2 = _phase2_input_hash(phase1_results)
        assert h1 != h2

    def test_changes_on_file_add(self, phase1_results):
        h1 = _phase2_input_hash(phase1_results)
        phase1_results["src/new.py"] = {"desc": "New file", "tags": ["python"]}
        h2 = _phase2_input_hash(phase1_results)
        assert h1 != h2

    def test_changes_on_tag_change(self, phase1_results):
        h1 = _phase2_input_hash(phase1_results)
        phase1_results["src/main.py"]["tags"] = ["cli", "python", "new-tag"]
        h2 = _phase2_input_hash(phase1_results)
        assert h1 != h2


class TestPhase3ModuleInputHash:
    def test_deterministic(self, phase1_results):
        h1 = _phase3_module_input_hash(
            "mod:core", "Core logic",
            ["src/main.py", "src/utils.py"], phase1_results,
        )
        h2 = _phase3_module_input_hash(
            "mod:core", "Core logic",
            ["src/main.py", "src/utils.py"], phase1_results,
        )
        assert h1 == h2

    def test_changes_on_member_desc_change(self, phase1_results):
        h1 = _phase3_module_input_hash(
            "mod:core", "Core logic",
            ["src/main.py", "src/utils.py"], phase1_results,
        )
        phase1_results["src/main.py"]["desc"] = "Changed"
        h2 = _phase3_module_input_hash(
            "mod:core", "Core logic",
            ["src/main.py", "src/utils.py"], phase1_results,
        )
        assert h1 != h2

    def test_changes_on_member_list_change(self, phase1_results):
        h1 = _phase3_module_input_hash(
            "mod:core", "Core logic",
            ["src/main.py", "src/utils.py"], phase1_results,
        )
        h2 = _phase3_module_input_hash(
            "mod:core", "Core logic",
            ["src/main.py"], phase1_results,
        )
        assert h1 != h2


# ── Cache persistence tests ──────────────────────────────────────


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
        loaded = _load_phase2_cache(out)
        assert loaded == data

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
                },
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
        loaded = _load_phase3_cache(out)
        assert loaded == data

    def test_phase3_cache_missing_returns_empty(self, tmp_path):
        out = tmp_path / ".hippocampus"
        out.mkdir()
        assert _load_phase3_cache(out) == {}


# ── Phase 2 integration tests ────────────────────────────────────


def _make_mock_config():
    """Create a minimal HippoConfig for testing."""
    from hippocampus.config import HippoConfig
    return HippoConfig()


def _mock_llm_2a_response():
    """Mock LLM response for Phase 2a (module vocab)."""
    return json.dumps({
        "modules": [
            {"id": "mod:core", "desc": "Core logic"},
            {"id": "mod:infra", "desc": "Infrastructure"},
        ]
    })


def _mock_llm_2b_response(files):
    """Mock LLM response for Phase 2b (file assignment)."""
    assignments = []
    for fp in files:
        mid = "mod:core" if "main" in fp or "utils" in fp else "mod:infra"
        assignments.append({"file": fp, "module_id": mid})
    return json.dumps(assignments)


class TestPhase2Incremental:
    """Test Phase 2 cache hit / miss / partial behavior."""

    @pytest.fixture
    def output_dir(self, tmp_path):
        out = tmp_path / ".hippocampus"
        out.mkdir()
        return out

    @pytest.mark.asyncio
    async def test_full_cache_hit_skips_llm(
        self, phase1_results, output_dir,
    ):
        """When cache matches, no LLM calls should be made."""
        config = _make_mock_config()

        # Pre-populate cache with matching hash
        current_hash = _phase2_input_hash(phase1_results)
        file_hashes = {}
        for fp, data in phase1_results.items():
            desc = data.get("desc", "")
            tags = ",".join(sorted(data.get("tags", [])))
            file_hashes[fp] = _content_hash(f"{fp}|{desc}|{tags}")

        modules = [
            {"id": "mod:core", "desc": "Core logic"},
            {"id": "mod:infra", "desc": "Infrastructure"},
        ]
        ftm = {
            "src/main.py": "mod:core",
            "src/utils.py": "mod:core",
            "src/config.py": "mod:infra",
            "src/server.py": "mod:infra",
        }
        _save_phase2_cache(output_dir, {
            "input_hash": current_hash,
            "modules": modules,
            "file_to_module": ftm,
            "file_hashes": file_hashes,
        })

        # Run phase_2 — should NOT call LLM
        with patch("hippocampus.tools.index_gen._phase2_full") as mock_full:
            with patch("hippocampus.tools.index_gen._phase2_partial_assign") as mock_partial:
                result_modules, result_ftm = await phase_2(
                    config, phase1_results,
                    output_dir=output_dir, verbose=True,
                )
                mock_full.assert_not_called()
                mock_partial.assert_not_called()

        assert result_modules == modules
        assert result_ftm == ftm

    @pytest.mark.asyncio
    async def test_cache_miss_calls_full(
        self, phase1_results, output_dir,
    ):
        """When no cache exists, _phase2_full should be called."""
        config = _make_mock_config()

        mock_modules = [{"id": "mod:core", "desc": "Core"}]
        mock_ftm = {"src/main.py": "mod:core"}

        with patch(
            "hippocampus.tools.index_gen._phase2_full",
            new_callable=AsyncMock,
            return_value=(mock_modules, mock_ftm),
        ) as mock_full:
            result_modules, result_ftm = await phase_2(
                config, phase1_results,
                output_dir=output_dir, verbose=True,
            )
            mock_full.assert_called_once()

        assert result_modules == mock_modules
        assert result_ftm == mock_ftm

    @pytest.mark.asyncio
    async def test_partial_hit_reassigns_only_changed(
        self, output_dir,
    ):
        """When <20% files changed, reuse modules and only re-assign delta."""
        config = _make_mock_config()

        # Use 6 files so 1 change = 16.7% < 20% threshold
        p1 = {
            "src/main.py": {"desc": "Entry point", "tags": ["cli", "python"]},
            "src/utils.py": {"desc": "Utility helpers", "tags": ["utils", "python"]},
            "src/config.py": {"desc": "Config loader", "tags": ["config", "python"]},
            "src/server.py": {"desc": "HTTP server", "tags": ["http", "python"]},
            "src/models.py": {"desc": "Data models", "tags": ["models", "python"]},
            "src/routes.py": {"desc": "API routes", "tags": ["api", "python"]},
        }

        # Build cache with current state
        file_hashes = {}
        for fp, data in p1.items():
            desc = data.get("desc", "")
            tags = ",".join(sorted(data.get("tags", [])))
            file_hashes[fp] = _content_hash(f"{fp}|{desc}|{tags}")

        modules = [
            {"id": "mod:core", "desc": "Core logic"},
            {"id": "mod:infra", "desc": "Infrastructure"},
        ]
        ftm = {
            "src/main.py": "mod:core",
            "src/utils.py": "mod:core",
            "src/models.py": "mod:core",
            "src/config.py": "mod:infra",
            "src/server.py": "mod:infra",
            "src/routes.py": "mod:infra",
        }

        old_hash = _phase2_input_hash(p1)
        _save_phase2_cache(output_dir, {
            "input_hash": old_hash,
            "modules": modules,
            "file_to_module": ftm,
            "file_hashes": file_hashes,
        })

        # Change 1 file (1/6 = 16.7% < 20% = partial hit)
        p1["src/main.py"]["desc"] = "Updated entry point"

        with patch(
            "hippocampus.tools.index_gen._phase2_partial_assign",
            new_callable=AsyncMock,
        ) as mock_partial:
            with patch(
                "hippocampus.tools.index_gen._phase2_full",
                new_callable=AsyncMock,
            ) as mock_full:
                await phase_2(
                    config, p1,
                    output_dir=output_dir, verbose=True,
                )
                mock_partial.assert_called_once()
                mock_full.assert_not_called()

                # Verify delta_files contains only the changed file
                call_args = mock_partial.call_args
                delta_files = call_args[0][2]  # 3rd positional arg
                assert delta_files == {"src/main.py"}


# ── Phase 3 integration tests ────────────────────────────────────


class TestPhase3Incremental:
    """Test Phase 3 cache hit / miss behavior."""

    @pytest.fixture
    def output_dir(self, tmp_path):
        out = tmp_path / ".hippocampus"
        out.mkdir()
        return out

    @pytest.fixture
    def target_dir(self, tmp_path):
        tgt = tmp_path / "project"
        tgt.mkdir()
        return tgt

    @pytest.mark.asyncio
    async def test_3a_cache_hit_skips_llm(
        self, phase1_results, modules_list, file_to_module,
        output_dir, target_dir,
    ):
        """When module content unchanged, 3a should skip LLM."""
        config = _make_mock_config()

        # Pre-populate Phase 3 cache
        cached_3a = {}
        for mod in modules_list:
            mid = mod["id"]
            mod_files = [
                fp for fp, m in file_to_module.items() if m == mid
            ]
            h = _phase3_module_input_hash(
                mid, mod["desc"], mod_files, phase1_results,
            )
            cached_3a[mid] = {
                "hash": h,
                "result": {
                    "desc": f"Cached desc for {mid}",
                    "key_files": mod_files[:1],
                },
            }

        _save_phase3_cache(output_dir, {
            "phase_3a": cached_3a,
            "phase_3b": {},
        })

        # Mock 3b LLM call (3b cache is empty so it will be called)
        mock_3b_result = {
            "overview": "Test project",
            "architecture": "modular",
            "scale": {"files": 4, "modules": 2, "primary_lang": "python"},
        }

        with patch(
            "hippocampus.tools.index_gen._phase3a_enrich_module",
            new_callable=AsyncMock,
        ) as mock_3a:
            with patch(
                "hippocampus.llm.client.HippoLLM",
            ) as MockLLM:
                mock_llm = MagicMock()
                mock_llm.call_with_retry = AsyncMock(
                    return_value=(json.dumps(mock_3b_result), []),
                )
                MockLLM.return_value = mock_llm

                result_modules, project = await phase_3(
                    config, modules_list, file_to_module,
                    phase1_results, target_dir,
                    output_dir=output_dir, verbose=True,
                )

                # 3a should NOT have been called (all cached)
                mock_3a.assert_not_called()

        # Verify cached desc was used
        for mod in result_modules:
            mid = mod["id"]
            assert mod["desc"] == f"Cached desc for {mid}"

    @pytest.mark.asyncio
    async def test_3a_cache_miss_calls_llm(
        self, phase1_results, modules_list, file_to_module,
        output_dir, target_dir,
    ):
        """When module content changed, 3a should call LLM for that module."""
        config = _make_mock_config()

        # Pre-populate cache for mod:core only (mod:infra will miss)
        mod_core_files = [
            fp for fp, m in file_to_module.items() if m == "mod:core"
        ]
        h = _phase3_module_input_hash(
            "mod:core", "Core logic", mod_core_files, phase1_results,
        )
        _save_phase3_cache(output_dir, {
            "phase_3a": {
                "mod:core": {
                    "hash": h,
                    "result": {"desc": "Cached core", "key_files": []},
                },
            },
            "phase_3b": {},
        })

        # Mock _phase3a_enrich_module for the cache-miss module
        async def fake_enrich(llm, mod, mod_files, p1):
            return {
                "id": mod["id"],
                "desc": f"LLM enriched {mod['id']}",
                "file_count": len(mod_files),
                "key_files": mod_files[:1],
            }

        mock_3b_result = {
            "overview": "Test", "architecture": "modular",
            "scale": {"files": 4, "modules": 2, "primary_lang": "python"},
        }

        with patch(
            "hippocampus.tools.index_gen._phase3a_enrich_module",
            side_effect=fake_enrich,
        ) as mock_3a:
            with patch(
                "hippocampus.llm.client.HippoLLM",
            ) as MockLLM:
                mock_llm = MagicMock()
                mock_llm.call_with_retry = AsyncMock(
                    return_value=(json.dumps(mock_3b_result), []),
                )
                MockLLM.return_value = mock_llm

                result_modules, _ = await phase_3(
                    config, modules_list, file_to_module,
                    phase1_results, target_dir,
                    output_dir=output_dir, verbose=True,
                )

                # Only mod:infra should have triggered LLM (1 call)
                assert mock_3a.call_count == 1
                called_mod = mock_3a.call_args[0][1]
                assert called_mod["id"] == "mod:infra"

        # mod:core should have cached desc
        core = [m for m in result_modules if m["id"] == "mod:core"][0]
        assert core["desc"] == "Cached core"
        # mod:infra should have LLM desc
        infra = [m for m in result_modules if m["id"] == "mod:infra"][0]
        assert infra["desc"] == "LLM enriched mod:infra"
