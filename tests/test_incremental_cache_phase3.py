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
            "hippocampus.tools.index.index_gen_phase3_runtime.create_llm_gateway"
        ) as MockGateway:
            mock_llm = MagicMock()
            mock_llm.run_json_task_with_retry = AsyncMock(
                return_value=type("Result", (), {"data": mock_3b_result, "errors": []})()
            )
            mock_llm.run_json_tasks_with_retry = AsyncMock(return_value=[])
            mock_llm.config = config
            MockGateway.return_value = mock_llm
            result_modules, _project = await phase_3(
                config,
                modules_list,
                file_to_module,
                phase1_results,
                target_dir,
                output_dir=output_dir,
                verbose=True,
            )
            mock_llm.run_json_tasks_with_retry.assert_not_called()

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

        mock_3b_result = {
            "overview": "Test",
            "architecture": "modular",
            "scale": {"files": 4, "modules": 2, "primary_lang": "python"},
        }
        with patch("hippocampus.tools.index.index_gen_phase3_runtime.create_llm_gateway") as MockGateway:
            mock_llm = MagicMock()
            mock_llm.run_json_task_with_retry = AsyncMock(
                return_value=type("Result", (), {"data": mock_3b_result, "errors": []})()
            )
            mock_llm.run_json_tasks_with_retry = AsyncMock(
                return_value=[
                    type("Result", (), {"data": {"desc": "LLM enriched mod:infra", "key_files": ["src/config.py"]}, "errors": []})()
                ]
            )
            mock_llm.config = config
            MockGateway.return_value = mock_llm
            result_modules, _ = await phase_3(
                config,
                modules_list,
                file_to_module,
                phase1_results,
                target_dir,
                output_dir=output_dir,
                verbose=True,
            )
            assert mock_llm.run_json_tasks_with_retry.call_count == 1
            requests = mock_llm.run_json_tasks_with_retry.call_args[0][0]
            assert len(requests) == 1
            assert requests[0].task == "phase_3a"

        core = [module for module in result_modules if module["id"] == "mod:core"][0]
        infra = [module for module in result_modules if module["id"] == "mod:infra"][0]
        assert core["desc"] == "Cached core"
        assert infra["desc"] == "LLM enriched mod:infra"

    @pytest.mark.asyncio
    async def test_3a_multiple_cache_misses_batch_through_run_tasks(
        self,
        phase1_results,
        modules_list,
        file_to_module,
        output_dir,
        target_dir,
    ):
        config = make_mock_config()
        mock_3b_result = {
            "overview": "Test",
            "architecture": "modular",
            "scale": {"files": 4, "modules": 2, "primary_lang": "python"},
        }
        with patch("hippocampus.tools.index.index_gen_phase3_runtime.create_llm_gateway") as MockGateway:
            mock_llm = MagicMock()
            mock_llm.run_json_task_with_retry = AsyncMock(
                return_value=type("Result", (), {"data": mock_3b_result, "errors": []})()
            )
            mock_llm.run_json_tasks_with_retry = AsyncMock(
                return_value=[
                    type("Result", (), {"data": {"desc": "LLM enriched mod:core", "key_files": ["src/main.py"]}, "errors": []})(),
                    type("Result", (), {"data": {"desc": "LLM enriched mod:infra", "key_files": ["src/config.py"]}, "errors": []})(),
                ]
            )
            mock_llm.config = config
            MockGateway.return_value = mock_llm
            result_modules, _ = await phase_3(
                config,
                modules_list,
                file_to_module,
                phase1_results,
                target_dir,
                output_dir=output_dir,
                verbose=True,
            )

            assert mock_llm.run_json_tasks_with_retry.call_count == 1
            requests = mock_llm.run_json_tasks_with_retry.call_args[0][0]
            assert len(requests) == 2
            assert [request.task for request in requests] == ["phase_3a", "phase_3a"]

        assert [module["desc"] for module in result_modules] == [
            "LLM enriched mod:core",
            "LLM enriched mod:infra",
        ]
