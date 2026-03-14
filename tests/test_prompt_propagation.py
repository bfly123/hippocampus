from __future__ import annotations

import json
from pathlib import Path

import pytest

from hippocampus.config import HippoConfig
from hippocampus.tools.architect_llm import LLMAnalyzer
from hippocampus.tools.index_gen_phase2 import phase2_assign_files, phase2_full
from hippocampus.tools.index_gen_phase3 import phase3a_enrich_module_impl


@pytest.mark.asyncio
async def test_phase2_full_passes_project_root(monkeypatch, tmp_path: Path):
    config = HippoConfig(target=str(tmp_path))
    seen: dict[str, object] = {}

    def fake_build_phase_2a_messages(*, project_root=None, **kwargs):
        seen["project_root"] = project_root
        seen["file_summaries"] = kwargs["file_summaries"]
        return [{"role": "user", "content": "x"}]

    async def fake_run_json_task_with_retry(self, phase, messages, validator):
        assert phase == "phase_2a"
        return type("Result", (), {"data": {"modules": [{"id": "core", "desc": "core module"}]}, "errors": []})()

    async def fake_assign(*args, **kwargs):
        return {"a.py": "core"}

    monkeypatch.setattr(
        "hippocampus.llm.prompts.build_phase_2a_messages",
        fake_build_phase_2a_messages,
    )
    class FakeGateway:
        async def run_json_task_with_retry(self, phase, messages, validator):
            return await fake_run_json_task_with_retry(self, phase, messages, validator)

    monkeypatch.setattr(
        "hippocampus.tools.index_gen_phase2.create_llm_gateway",
        lambda _config: FakeGateway(),
    )
    monkeypatch.setattr(
        "hippocampus.tools.index_gen_phase2.phase2_assign_files",
        fake_assign,
    )

    modules, file_to_module = await phase2_full(
        config,
        {"a.py": {"desc": "alpha", "tags": ["core"]}},
    )

    assert seen["project_root"] == tmp_path.resolve()
    assert "a.py: alpha [core]" in str(seen["file_summaries"])
    assert modules[0]["id"] == "core"
    assert file_to_module["a.py"] == "core"


@pytest.mark.asyncio
async def test_phase2_assign_files_batches_through_gateway(monkeypatch, tmp_path: Path):
    config = HippoConfig(target=str(tmp_path))
    seen: dict[str, object] = {}

    def fake_build_phase_2b_messages(*, project_root=None, **kwargs):
        seen.setdefault("project_roots", []).append(project_root)
        seen.setdefault("file_counts", []).append(kwargs["file_count"])
        seen.setdefault("file_summaries", []).append(kwargs["file_summaries"])
        return [{"role": "user", "content": "x"}]

    class FakeGateway:
        async def run_json_tasks_with_retry(self, requests, validators):
            seen["request_count"] = len(requests)
            seen["validator_count"] = len(validators)
            return [
                type("Result", (), {"data": [{"file": "file_01.py", "module_id": "mod:core"}], "errors": []})(),
                type("Result", (), {"data": [{"file": "file_65.py", "module_id": "mod:infra"}], "errors": []})(),
            ]

    monkeypatch.setattr(
        "hippocampus.llm.prompts.build_phase_2b_messages",
        fake_build_phase_2b_messages,
    )
    monkeypatch.setattr(
        "hippocampus.tools.index_gen_phase2.create_llm_gateway",
        lambda _config: FakeGateway(),
    )

    phase1_results = {
        f"file_{idx:02d}.py": {"desc": f"file {idx}", "tags": ["python"]}
        for idx in range(1, 66)
    }
    modules = [
        {"id": "mod:core", "desc": "core"},
        {"id": "mod:infra", "desc": "infra"},
    ]

    assignments = await phase2_assign_files(
        config,
        modules,
        phase1_results,
        set(phase1_results.keys()),
    )

    assert seen["request_count"] == 2
    assert seen["validator_count"] == 2
    assert seen["file_counts"] == [64, 1]
    assert seen["project_roots"] == [tmp_path.resolve(), tmp_path.resolve()]
    assert assignments["file_01.py"] == "mod:core"
    assert assignments["file_65.py"] == "mod:infra"


@pytest.mark.asyncio
async def test_phase3a_passes_project_root(monkeypatch, tmp_path: Path):
    seen: dict[str, object] = {}

    def fake_build_phase_3a_messages(*, project_root=None, **kwargs):
        seen["project_root"] = project_root
        seen["module_id"] = kwargs["module_id"]
        return [{"role": "user", "content": "x"}]

    async def fake_run_json_task_with_retry(self, phase, messages, validator):
        assert phase == "phase_3a"
        return type("Result", (), {"data": {"desc": "enriched", "key_files": ["a.py"]}, "errors": []})()

    class FakeLLM:
        config = HippoConfig(target=str(tmp_path))

        async def run_json_task_with_retry(self, phase, messages, validator):
            return await fake_run_json_task_with_retry(self, phase, messages, validator)

    monkeypatch.setattr(
        "hippocampus.llm.prompts.build_phase_3a_messages",
        fake_build_phase_3a_messages,
    )

    enriched = await phase3a_enrich_module_impl(
        FakeLLM(),
        {"id": "core", "desc": "core"},
        ["a.py"],
        {"a.py": {"desc": "alpha"}},
        project_root=tmp_path.resolve(),
    )

    assert seen["project_root"] == tmp_path.resolve()
    assert seen["module_id"] == "core"
    assert enriched["desc"] == "enriched"
    assert enriched["key_files"] == ["a.py"]


@pytest.mark.asyncio
async def test_architect_plan_passes_project_root(monkeypatch, tmp_path: Path):
    seen: dict[str, object] = {}

    def fake_build_architect_plan_messages(*, project_root=None, **kwargs):
        seen["project_root"] = project_root
        seen["description"] = kwargs["description"]
        return [{"role": "user", "content": "x"}]

    async def fake_run_json_task(self, phase, messages):
        assert phase == "architect"
        return type("Result", (), {"data": {"summary": "ok"}})()

    monkeypatch.setattr(
        "hippocampus.tools.architect_llm.build_architect_plan_messages",
        fake_build_architect_plan_messages,
    )
    class FakeGateway:
        async def run_json_task(self, phase, messages):
            return await fake_run_json_task(self, phase, messages)

    monkeypatch.setattr(
        "hippocampus.tools.architect_llm.create_llm_gateway",
        lambda _config: FakeGateway(),
    )

    analyzer = LLMAnalyzer(HippoConfig(target=str(tmp_path)))

    result = await analyzer.plan_feature({"project": "demo", "stats": {}, "modules": []}, "add cache")

    assert seen["project_root"] == tmp_path.resolve()
    assert seen["description"] == "add cache"
    assert result["summary"] == "ok"
