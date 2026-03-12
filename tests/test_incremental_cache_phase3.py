"""Tests for Phase 3 incremental cache behavior."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hippocampus.tools.index_gen import phase_3

from incremental_cache_helpers import (
    _phase3_module_input_hash,
    _save_phase3_cache,
    file_to_module,
    make_mock_config,
    modules_list,
    phase1_results,
)


class TestPhase3Incremental:
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
        self,
        phase1_results,
        modules_list,
        file_to_module,
        output_dir,
        target_dir,
    ):
        config = make_mock_config()
        cached_3a = {}
        for module in modules_list:
            module_id = module["id"]
            mod_files = [file_path for file_path, mid in file_to_module.items() if mid == module_id]
            cached_3a[module_id] = {
                "hash": _phase3_module_input_hash(
                    module_id,
                    module["desc"],
                    mod_files,
                    phase1_results,
                ),
                "result": {
                    "desc": f"Cached desc for {module_id}",
                    "key_files": mod_files[:1],
                },
            }
        _save_phase3_cache(output_dir, {"phase_3a": cached_3a, "phase_3b": {}})

        mock_3b_result = {
            "overview": "Test project",
            "architecture": "modular",
            "scale": {"files": 4, "modules": 2, "primary_lang": "python"},
        }
        with patch(
            "hippocampus.tools.index_gen._phase3a_enrich_module",
            new_callable=AsyncMock,
        ) as mock_3a:
            with patch("hippocampus.llm.client.HippoLLM") as MockLLM:
                mock_llm = MagicMock()
                mock_llm.call_with_retry = AsyncMock(return_value=(json.dumps(mock_3b_result), []))
                MockLLM.return_value = mock_llm
                result_modules, _project = await phase_3(
                    config,
                    modules_list,
                    file_to_module,
                    phase1_results,
                    target_dir,
                    output_dir=output_dir,
                    verbose=True,
                )
                mock_3a.assert_not_called()

        for module in result_modules:
            assert module["desc"] == f"Cached desc for {module['id']}"

    @pytest.mark.asyncio
    async def test_3a_cache_miss_calls_llm(
        self,
        phase1_results,
        modules_list,
        file_to_module,
        output_dir,
        target_dir,
    ):
        config = make_mock_config()
        mod_core_files = [file_path for file_path, mid in file_to_module.items() if mid == "mod:core"]
        _save_phase3_cache(
            output_dir,
            {
                "phase_3a": {
                    "mod:core": {
                        "hash": _phase3_module_input_hash(
                            "mod:core",
                            "Core logic",
                            mod_core_files,
                            phase1_results,
                        ),
                        "result": {"desc": "Cached core", "key_files": []},
                    }
                },
                "phase_3b": {},
            },
        )

        async def fake_enrich(llm, mod, mod_files, phase1):
            return {
                "id": mod["id"],
                "desc": f"LLM enriched {mod['id']}",
                "file_count": len(mod_files),
                "key_files": mod_files[:1],
            }

        mock_3b_result = {
            "overview": "Test",
            "architecture": "modular",
            "scale": {"files": 4, "modules": 2, "primary_lang": "python"},
        }
        with patch(
            "hippocampus.tools.index_gen._phase3a_enrich_module",
            side_effect=fake_enrich,
        ) as mock_3a:
            with patch("hippocampus.llm.client.HippoLLM") as MockLLM:
                mock_llm = MagicMock()
                mock_llm.call_with_retry = AsyncMock(return_value=(json.dumps(mock_3b_result), []))
                MockLLM.return_value = mock_llm
                result_modules, _ = await phase_3(
                    config,
                    modules_list,
                    file_to_module,
                    phase1_results,
                    target_dir,
                    output_dir=output_dir,
                    verbose=True,
                )
                assert mock_3a.call_count == 1
                assert mock_3a.call_args[0][1]["id"] == "mod:infra"

        core = [module for module in result_modules if module["id"] == "mod:core"][0]
        infra = [module for module in result_modules if module["id"] == "mod:infra"][0]
        assert core["desc"] == "Cached core"
        assert infra["desc"] == "LLM enriched mod:infra"
