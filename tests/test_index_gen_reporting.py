from __future__ import annotations

from pathlib import Path

import pytest

from hippocampus.tools.index_gen_reporting import (
    format_failed_file_summary,
    format_phase_duration,
    format_progress_bar,
    format_progress_line,
)
from hippocampus.tools.index_gen_runtime import run_index_pipeline_impl


def test_format_phase_duration():
    assert format_phase_duration(0.25) == "250ms"
    assert format_phase_duration(3.2) == "3.2s"
    assert format_phase_duration(65.4) == "1m05.4s"


def test_format_failed_file_summary():
    summary = format_failed_file_summary(
        [f"file_{idx}.py" for idx in range(12)],
        total_processed=30,
    )
    assert summary.startswith("Phase 1 failed files: 12/30")
    assert "... +2 more" in summary


def test_format_progress_helpers():
    assert format_progress_bar(3, 10, width=10) == "[###.......]"
    line = format_progress_line("Phase X", 3, 10, detail="running", width=10)
    assert line == "Phase X: [###.......] 3/10 ( 30.0%) | running"


@pytest.mark.asyncio
async def test_run_index_pipeline_impl_prints_phase_durations(tmp_path: Path, capsys):
    async def phase_0_fn(target: Path, output_dir: Path, verbose: bool):
        del target, output_dir, verbose
        return {"compress": {}, "signatures": {}}

    async def phase_1_fn(*args, **kwargs):
        del args, kwargs
        return {}

    async def phase_2_fn(*args, **kwargs):
        del args, kwargs
        return [], {}

    async def phase_3_fn(*args, **kwargs):
        del args, kwargs
        return [], {"overview": "", "architecture": "", "scale": {"files": 0, "modules": 0, "primary_lang": "python"}}

    def phase_4_merge_fn(**kwargs):
        del kwargs
        return {
            "stats": {"total_files": 0, "total_modules": 0, "total_signatures": 0},
            "project": {"overview": "", "architecture": "", "scale": {"files": 0, "modules": 0, "primary_lang": "python"}},
        }

    async def cleanup_fn():
        return None

    await run_index_pipeline_impl(
        target=tmp_path,
        output_dir=tmp_path / ".hippocampus",
        phase=None,
        verbose=True,
        no_llm=False,
        phase_0_fn=phase_0_fn,
        phase_1_fn=phase_1_fn,
        phase_2_fn=phase_2_fn,
        phase_3_fn=phase_3_fn,
        phase_4_merge_fn=phase_4_merge_fn,
        cleanup_fn=cleanup_fn,
        config=object(),
    )

    captured = capsys.readouterr().out
    assert "Phase 0 done in" in captured
    assert "Phase 1 done in" in captured
    assert "Phase 2 done in" in captured
    assert "Phase 3 done in" in captured
    assert "Phase 4 done in" in captured
