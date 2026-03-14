from __future__ import annotations

import asyncio

import pytest
from llmgateway import LLMService, TaskRequest
from llmgateway.runtime import (
    normalize_model_request,
    prefers_anthropic_messages,
    prefers_openai_chat,
    prefers_openai_responses,
)
from llmgateway.transport_payloads import (
    build_openai_chat_url,
    build_openai_responses_payload,
    build_openai_responses_url,
)

from hippocampus.config import HippoConfig
from hippocampus.llm.adapters import runtime_spec_from_hippo_config
from hippocampus.llm.gateway import LLMGateway
from hippocampus.user_llm_config import build_user_llm_config


def _provider_dict(cfg: HippoConfig) -> dict[str, object]:
    provider = runtime_spec_from_hippo_config(cfg).provider
    return {
        "provider_type": provider.provider_type,
        "api_style": provider.api_style,
        "base_url": provider.base_url,
        "api_key": provider.api_key,
        "headers": dict(provider.headers),
        "model_map": dict(provider.model_map),
    }


def test_user_llm_config_defaults_to_codex_style():
    payload = build_user_llm_config(
        base_url="https://backend.example/v1",
        api_key="secret",
        model="gpt-5.3-codex high",
    )
    assert payload["providers"]["main"]["provider_type"] == "glm"
    assert payload["providers"]["main"]["api_style"] == "openai_responses"


def test_runtime_prefers_openai_responses_for_glm():
    cfg = HippoConfig.model_validate(
        {
            "llm": {
                "provider_type": "glm",
                "api_style": "openai_responses",
                "base_url": "https://backend.example/v1",
                "api_key": "secret",
                "fallback_model": "gpt-5.3-codex high",
            }
        }
    )
    provider = _provider_dict(cfg)
    assert prefers_openai_responses(provider) is True
    assert prefers_openai_chat(provider) is False
    assert prefers_anthropic_messages(provider, "gpt-5.3-codex high") is False


def test_normalize_model_request_strips_responses_quality_suffix():
    cfg = HippoConfig.model_validate(
        {
            "llm": {
                "provider_type": "glm",
                "api_style": "openai_responses",
                "base_url": "https://backend.example/v1",
                "api_key": "secret",
                "fallback_model": "gpt-5.3-codex high",
            }
        }
    )
    provider = _provider_dict(cfg)
    assert normalize_model_request(provider, "gpt-5.3-codex high")[0] == "gpt-5.3-codex"


def test_normalize_model_request_extracts_reasoning_effort():
    provider = {
        "provider_type": "glm",
        "api_style": "openai_responses",
        "base_url": "https://backend.example/v1",
    }
    model, effort = normalize_model_request(provider, "openai/gpt-5.4 high")
    assert model == "openai/gpt-5.4"
    assert effort == "high"


def test_openai_responses_url_builder():
    provider = {"base_url": "https://backend.example/v1"}
    assert build_openai_responses_url(provider) == "https://backend.example/v1/responses"
    assert build_openai_chat_url(provider) == "https://backend.example/v1/chat/completions"


def test_openai_responses_payload_uses_instructions():
    payload = build_openai_responses_payload(
        model="gpt-5.3-codex high",
        messages=[
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "hello"},
        ],
        max_tokens=200,
        temperature=1.0,
    )
    assert payload["model"] == "gpt-5.3-codex high"
    assert payload["instructions"] == "system prompt"
    assert payload["input"][0]["role"] == "user"


def test_openai_responses_payload_includes_reasoning_effort():
    payload = build_openai_responses_payload(
        model="openai/gpt-5.4",
        messages=[{"role": "user", "content": "hello"}],
        max_tokens=200,
        temperature=1.0,
        reasoning_effort="high",
    )
    assert payload["reasoning"] == {"effort": "high"}


@pytest.mark.asyncio
async def test_llm_call_raises_when_base_url_missing():
    cfg = HippoConfig()
    llm = LLMGateway(cfg)
    with pytest.raises(RuntimeError, match="base_url is not configured"):
        await llm.run_task("phase_1", [{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_llm_call_passes_reasoning_effort_to_openai_responses(monkeypatch):
    cfg = HippoConfig.model_validate(
        {
            "llm": {
                "provider_type": "glm",
                "api_style": "openai_responses",
                "base_url": "https://backend.example/v1",
                "api_key": "secret",
                "phase_models": {
                    "phase_1": "openai/gpt-5.4",
                    "phase_2a": "openai/gpt-5.4",
                    "phase_2b": "openai/gpt-5.4",
                    "phase_3a": "openai/gpt-5.4",
                    "phase_3b": "openai/gpt-5.4",
                    "architect": "openai/gpt-5.4",
                },
                "phase_reasoning_effort": {
                    "phase_1": "low",
                    "phase_2a": "high",
                    "phase_2b": "low",
                    "phase_3a": "low",
                    "phase_3b": "high",
                    "architect": "high",
                },
            }
        }
    )
    llm = LLMGateway(cfg)
    seen: dict[str, str] = {}

    async def fake_completion(**kwargs):
        seen["model"] = kwargs["model"]
        seen["reasoning_effort"] = kwargs.get("reasoning_effort", "")
        return '{"ok": true}'

    monkeypatch.setattr("llmgateway.service.openai_responses_completion", fake_completion)

    text = await llm.run_task("phase_2a", [{"role": "user", "content": "x"}])

    assert text == '{"ok": true}'
    assert seen["model"] == "openai/gpt-5.4"
    assert seen["reasoning_effort"] == "high"


@pytest.mark.asyncio
async def test_call_with_retry_retries_on_transport_exception(monkeypatch):
    cfg = HippoConfig.model_validate(
        {
            "llm": {
                "provider_type": "glm",
                "api_style": "openai_responses",
                "base_url": "https://backend.example/v1",
                "api_key": "secret",
                "retry_max": 2,
            }
        }
    )
    llm = LLMGateway(cfg)
    attempts = {"n": 0}

    async def fake_generate_text(_request):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("502 Bad Gateway")
        return '{"ok": true}'

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(llm.service, "generate_text", fake_generate_text)
    monkeypatch.setattr(llm.service, "_sleep", fake_sleep)

    text, errors = await llm.run_task_with_retry(
        "phase_2b",
        [{"role": "user", "content": "x"}],
        lambda _text: [],
    )

    assert attempts["n"] == 2
    assert text == '{"ok": true}'
    assert errors == []


@pytest.mark.asyncio
async def test_call_with_retry_raises_after_transport_retries(monkeypatch):
    cfg = HippoConfig.model_validate(
        {
            "llm": {
                "provider_type": "glm",
                "api_style": "openai_responses",
                "base_url": "https://backend.example/v1",
                "api_key": "secret",
                "retry_max": 1,
            }
        }
    )
    llm = LLMGateway(cfg)

    async def always_fail(_request):
        raise RuntimeError("502 Bad Gateway")

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(llm.service, "generate_text", always_fail)
    monkeypatch.setattr(llm.service, "_sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="502 Bad Gateway"):
        await llm.run_task_with_retry("phase_2b", [{"role": "user", "content": "x"}], lambda _text: [])


def test_runtime_spec_from_hippo_config_exposes_generic_provider_and_tasks():
    cfg = HippoConfig.model_validate(
        {
            "llm": {
                "provider_type": "glm",
                "api_style": "openai_responses",
                "base_url": "https://backend.example/v1",
                "api_key": "secret",
                "max_concurrent": 12,
                "retry_max": 4,
                "timeout": 45,
                "phase_models": {
                    "phase_1": "gpt-5.4",
                    "phase_2a": "gpt-5.4",
                    "phase_2b": "gpt-5.4",
                    "phase_3a": "gpt-5.4",
                    "phase_3b": "gpt-5.4",
                    "architect": "gpt-5.4",
                },
                "phase_reasoning_effort": {
                    "phase_1": "low",
                    "phase_2a": "high",
                    "phase_2b": "low",
                    "phase_3a": "low",
                    "phase_3b": "high",
                    "architect": "high",
                },
            }
        }
    )
    runtime = runtime_spec_from_hippo_config(cfg)
    assert runtime.provider.base_url == "https://backend.example/v1"
    assert runtime.max_concurrent == 12
    assert runtime.retry_max == 4
    assert runtime.timeout == 45.0
    assert runtime.task("phase_2a").model == "gpt-5.4"
    assert runtime.task("phase_2a").reasoning_effort == "high"


@pytest.mark.asyncio
async def test_llm_service_run_many_respects_max_concurrent(monkeypatch):
    cfg = HippoConfig.model_validate(
        {
            "llm": {
                "provider_type": "glm",
                "api_style": "openai_responses",
                "base_url": "https://backend.example/v1",
                "api_key": "secret",
                "max_concurrent": 2,
                "phase_models": {
                    "phase_1": "gpt-5.4",
                    "phase_2a": "gpt-5.4",
                    "phase_2b": "gpt-5.4",
                    "phase_3a": "gpt-5.4",
                    "phase_3b": "gpt-5.4",
                    "architect": "gpt-5.4",
                },
            }
        }
    )
    service = LLMService(runtime_spec_from_hippo_config(cfg))
    state = {"inflight": 0, "max_seen": 0}

    async def fake_complete_once(**kwargs):
        state["inflight"] += 1
        state["max_seen"] = max(state["max_seen"], state["inflight"])
        await asyncio.sleep(0.01)
        state["inflight"] -= 1
        return f"OK {kwargs['model']}"

    monkeypatch.setattr(service, "_complete_once", fake_complete_once)

    results = await service.run_many(
        [
            TaskRequest(task="phase_1", messages=[{"role": "user", "content": str(i)}])
            for i in range(5)
        ]
    )

    assert len(results) == 5
    assert all(result.text.startswith("OK") for result in results)
    assert state["max_seen"] == 2


@pytest.mark.asyncio
async def test_llm_gateway_delegates_to_service(monkeypatch):
    cfg = HippoConfig.model_validate(
        {
            "llm": {
                "provider_type": "glm",
                "api_style": "openai_responses",
                "base_url": "https://backend.example/v1",
                "api_key": "secret",
                "phase_models": {
                    "phase_1": "gpt-5.4",
                    "phase_2a": "gpt-5.4",
                    "phase_2b": "gpt-5.4",
                    "phase_3a": "gpt-5.4",
                    "phase_3b": "gpt-5.4",
                    "architect": "gpt-5.4",
                },
            }
        }
    )
    gateway = LLMGateway(cfg)

    async def fake_generate_text_with_retry(request, validator=None):
        del validator
        return f"OK {request.task}", []

    monkeypatch.setattr(gateway.service, "generate_text_with_retry", fake_generate_text_with_retry)

    text, errors = await gateway.run_task_with_retry(
        "phase_3a",
        [{"role": "user", "content": "hello"}],
    )

    assert text == "OK phase_3a"
    assert errors == []


@pytest.mark.asyncio
async def test_llm_gateway_run_json_task_parses_object(monkeypatch):
    cfg = HippoConfig.model_validate(
        {
            "llm": {
                "provider_type": "glm",
                "api_style": "openai_responses",
                "base_url": "https://backend.example/v1",
                "api_key": "secret",
                "phase_models": {
                    "phase_1": "gpt-5.4",
                    "phase_2a": "gpt-5.4",
                    "phase_2b": "gpt-5.4",
                    "phase_3a": "gpt-5.4",
                    "phase_3b": "gpt-5.4",
                    "architect": "gpt-5.4",
                },
            }
        }
    )
    gateway = LLMGateway(cfg)

    async def fake_generate_text(request):
        assert request.task == "architect"
        return '```json\n{"summary":"ok"}\n```'

    monkeypatch.setattr(gateway.service, "generate_text", fake_generate_text)

    result = await gateway.run_json_task(
        "architect",
        [{"role": "user", "content": "hello"}],
    )

    assert result.data == {"summary": "ok"}
    assert result.text.startswith("```json")


@pytest.mark.asyncio
async def test_llm_service_run_many_with_retry_respects_max_concurrent(monkeypatch):
    cfg = HippoConfig.model_validate(
        {
            "llm": {
                "provider_type": "glm",
                "api_style": "openai_responses",
                "base_url": "https://backend.example/v1",
                "api_key": "secret",
                "max_concurrent": 2,
                "retry_max": 0,
                "phase_models": {
                    "phase_1": "gpt-5.4",
                    "phase_2a": "gpt-5.4",
                    "phase_2b": "gpt-5.4",
                    "phase_3a": "gpt-5.4",
                    "phase_3b": "gpt-5.4",
                    "architect": "gpt-5.4",
                },
            }
        }
    )
    service = LLMService(runtime_spec_from_hippo_config(cfg))
    state = {"inflight": 0, "max_seen": 0}

    async def fake_complete_once(**kwargs):
        state["inflight"] += 1
        state["max_seen"] = max(state["max_seen"], state["inflight"])
        await asyncio.sleep(0.01)
        state["inflight"] -= 1
        return f"OK {kwargs['model']}"

    monkeypatch.setattr(service, "_complete_once", fake_complete_once)

    results = await service.run_many_with_retry(
        [
            TaskRequest(task="phase_3a", messages=[{"role": "user", "content": str(i)}])
            for i in range(5)
        ]
    )

    assert len(results) == 5
    assert all(text.startswith("OK") and errors == [] for text, errors in results)
    assert state["max_seen"] == 2
