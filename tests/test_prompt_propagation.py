from __future__ import annotations

import json
from pathlib import Path

import pytest

from hippocampus.config import HippoConfig
from hippocampus.tools.architect_llm import LLMAnalyzer
from hippocampus.tools.index_gen_phase2 import phase2_full
from hippocampus.tools.index_gen_phase3 import phase3a_enrich_module_impl


@pytest.mark.asyncio
async def test_phase2_full_passes_project_root(monkeypatch, tmp_path: Path):
    config = HippoConfig(target=str(tmp_path))
    seen: dict[str, object] = {}

    def fake_build_phase_2a_messages(*, project_root=None, **kwargs):
        seen["project_root"] = project_root
        seen["file_summaries"] = kwargs["file_summaries"]
        return [{"role": "user", "content": "x"}]

    async def fake_call_with_retry(self, phase, messages, validator):
        assert phase == "phase_2a"
        return json.dumps({"modules": [{"id": "core", "desc": "core module"}]}), []

    async def fake_assign(*args, **kwargs):
        return {"a.py": "core"}

    monkeypatch.setattr(
        "hippocampus.llm.prompts.build_phase_2a_messages",
        fake_build_phase_2a_messages,
    )
    monkeypatch.setattr(
        "hippocampus.llm.client.HippoLLM.call_with_retry",
        fake_call_with_retry,
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
async def test_phase3a_passes_project_root(monkeypatch, tmp_path: Path):
    seen: dict[str, object] = {}

    def fake_build_phase_3a_messages(*, project_root=None, **kwargs):
        seen["project_root"] = project_root
        seen["module_id"] = kwargs["module_id"]
        return [{"role": "user", "content": "x"}]

    async def fake_call_with_retry(self, phase, messages, validator):
        assert phase == "phase_3a"
        return json.dumps({"desc": "enriched", "key_files": ["a.py"]}), []

    class FakeLLM:
        config = HippoConfig(target=str(tmp_path))

        async def call_with_retry(self, phase, messages, validator):
            return await fake_call_with_retry(self, phase, messages, validator)

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
    analyzer = LLMAnalyzer(HippoConfig(target=str(tmp_path)))
    seen: dict[str, object] = {}

    def fake_build_architect_plan_messages(*, project_root=None, **kwargs):
        seen["project_root"] = project_root
        seen["description"] = kwargs["description"]
        return [{"role": "user", "content": "x"}]

    async def fake_call(self, phase, messages):
        assert phase == "architect"
        return json.dumps({"summary": "ok"})

    monkeypatch.setattr(
        "hippocampus.tools.architect_llm.build_architect_plan_messages",
        fake_build_architect_plan_messages,
    )
    monkeypatch.setattr(
        "hippocampus.llm.client.HippoLLM.call",
        fake_call,
    )

    result = await analyzer.plan_feature({"project": "demo", "stats": {}, "modules": []}, "add cache")

    assert seen["project_root"] == tmp_path.resolve()
    assert seen["description"] == "add cache"
    assert result["summary"] == "ok"
