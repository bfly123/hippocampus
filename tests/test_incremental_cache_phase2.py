"""Tests for Phase 2 incremental cache behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from hippocampus.tools.index_gen import phase_2

from incremental_cache_helpers import (
    _content_hash,
    _phase2_input_hash,
    _save_phase2_cache,
    make_mock_config,
    phase1_results,
)


class TestPhase2Incremental:
    @pytest.fixture
    def output_dir(self, tmp_path):
        out = tmp_path / ".hippocampus"
        out.mkdir()
        return out

    @pytest.mark.asyncio
    async def test_full_cache_hit_skips_llm(self, phase1_results, output_dir):
        config = make_mock_config()
        current_hash = _phase2_input_hash(phase1_results)
        file_hashes = {}
        for file_path, data in phase1_results.items():
            desc = data.get("desc", "")
            tags = ",".join(sorted(data.get("tags", [])))
            file_hashes[file_path] = _content_hash(f"{file_path}|{desc}|{tags}")

        modules = [
            {"id": "mod:core", "desc": "Core logic"},
            {"id": "mod:infra", "desc": "Infrastructure"},
        ]
        file_to_module = {
            "src/main.py": "mod:core",
            "src/utils.py": "mod:core",
            "src/config.py": "mod:infra",
            "src/server.py": "mod:infra",
        }
        _save_phase2_cache(
            output_dir,
            {
                "input_hash": current_hash,
                "modules": modules,
                "file_to_module": file_to_module,
                "file_hashes": file_hashes,
            },
        )

        with patch("hippocampus.tools.index_gen._phase2_full") as mock_full:
            with patch("hippocampus.tools.index_gen._phase2_partial_assign") as mock_partial:
                result_modules, result_ftm = await phase_2(
                    config,
                    phase1_results,
                    output_dir=output_dir,
                    verbose=True,
                )
                mock_full.assert_not_called()
                mock_partial.assert_not_called()

        assert result_modules == modules
        assert result_ftm == file_to_module

    @pytest.mark.asyncio
    async def test_cache_miss_calls_full(self, phase1_results, output_dir):
        config = make_mock_config()
        mock_modules = [{"id": "mod:core", "desc": "Core"}]
        mock_ftm = {"src/main.py": "mod:core"}

        with patch(
            "hippocampus.tools.index_gen._phase2_full",
            new_callable=AsyncMock,
            return_value=(mock_modules, mock_ftm),
        ) as mock_full:
            result_modules, result_ftm = await phase_2(
                config,
                phase1_results,
                output_dir=output_dir,
                verbose=True,
            )
            mock_full.assert_called_once()

        assert result_modules == mock_modules
        assert result_ftm == mock_ftm

    @pytest.mark.asyncio
    async def test_partial_hit_reassigns_only_changed(self, output_dir):
        config = make_mock_config()
        phase1 = {
            "src/main.py": {"desc": "Entry point", "tags": ["cli", "python"]},
            "src/utils.py": {"desc": "Utility helpers", "tags": ["utils", "python"]},
            "src/config.py": {"desc": "Config loader", "tags": ["config", "python"]},
            "src/server.py": {"desc": "HTTP server", "tags": ["http", "python"]},
            "src/models.py": {"desc": "Data models", "tags": ["models", "python"]},
            "src/routes.py": {"desc": "API routes", "tags": ["api", "python"]},
        }
        file_hashes = {}
        for file_path, data in phase1.items():
            desc = data.get("desc", "")
            tags = ",".join(sorted(data.get("tags", [])))
            file_hashes[file_path] = _content_hash(f"{file_path}|{desc}|{tags}")

        modules = [
            {"id": "mod:core", "desc": "Core logic"},
            {"id": "mod:infra", "desc": "Infrastructure"},
        ]
        file_to_module = {
            "src/main.py": "mod:core",
            "src/utils.py": "mod:core",
            "src/models.py": "mod:core",
            "src/config.py": "mod:infra",
            "src/server.py": "mod:infra",
            "src/routes.py": "mod:infra",
        }
        _save_phase2_cache(
            output_dir,
            {
                "input_hash": _phase2_input_hash(phase1),
                "modules": modules,
                "file_to_module": file_to_module,
                "file_hashes": file_hashes,
            },
        )

        phase1["src/main.py"]["desc"] = "Updated entry point"
        with patch(
            "hippocampus.tools.index_gen._phase2_partial_assign",
            new_callable=AsyncMock,
        ) as mock_partial:
            with patch(
                "hippocampus.tools.index_gen._phase2_full",
                new_callable=AsyncMock,
            ) as mock_full:
                await phase_2(config, phase1, output_dir=output_dir, verbose=True)
                mock_partial.assert_called_once()
                mock_full.assert_not_called()
                assert mock_partial.call_args[0][2] == {"src/main.py"}
