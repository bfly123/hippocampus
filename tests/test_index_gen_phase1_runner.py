from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from hippocampus.tools.index_gen_phase1 import phase_1_impl


@pytest.mark.asyncio
async def test_phase1_impl_processes_files_concurrently(tmp_path: Path, monkeypatch):
    running = 0
    max_running = 0

    class FakeLLM:
        async def run_json_task_with_retry(self, phase, messages, validator):
            nonlocal running, max_running
            assert phase == "phase_1"
            assert messages
            running += 1
            max_running = max(max_running, running)
            await asyncio.sleep(0.02)
            running -= 1
            return type(
                "Result",
                (),
                {"data": {"desc": "ok", "tags": ["core"], "signatures": []}, "errors": []},
            )()

    monkeypatch.setattr(
        "hippocampus.tools.index_gen_phase1.create_llm_gateway",
        lambda _config: FakeLLM(),
    )

    phase0_data = {
        "signatures": SimpleNamespace(
            files={
                f"file_{idx}.py": SimpleNamespace(signatures=[], lang="python")
                for idx in range(5)
            }
        ),
        "compress": {
            "files": {f"file_{idx}.py": "print('x')" for idx in range(5)}
        },
    }

    def load_cache(_output_dir: Path) -> dict[str, dict]:
        return {}

    def save_cache(_output_dir: Path, _cache: dict[str, dict]) -> None:
        return None

    results = await phase_1_impl(
        config=SimpleNamespace(llm=SimpleNamespace(max_concurrent=20, retry_max=1, timeout=30)),
        phase0_data=phase0_data,
        target=tmp_path,
        output_dir=tmp_path / ".hippocampus",
        dir_tree="",
        verbose=False,
        content_hash_fn=lambda text: text,
        load_phase1_cache_fn=load_cache,
        save_phase1_cache_fn=save_cache,
        detect_lang_hint_fn=lambda target: "python",
    )

    assert len(results) == 5
    assert max_running > 1
