from __future__ import annotations

from hippocampus.config import HippoConfig
from hippocampus.llm.runtime import (
    llm_provider,
    normalize_model_name,
    prefers_anthropic_messages,
    prefers_openai_chat,
    prefers_openai_responses,
)
from hippocampus.llm.transport_payloads import (
    build_openai_chat_url,
    build_openai_responses_payload,
    build_openai_responses_url,
)
from hippocampus.user_llm_config import build_user_llm_config


def test_user_llm_config_defaults_to_codex_style():
    payload = build_user_llm_config(
        base_url="https://backend.example/v1",
        api_key="secret",
        model="gpt-5.3-codex high",
    )
    assert payload["llm"]["provider_type"] == "glm"
    assert payload["llm"]["api_style"] == "openai_responses"


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
    provider = llm_provider(cfg)
    assert prefers_openai_responses(provider) is True
    assert prefers_openai_chat(provider) is False
    assert prefers_anthropic_messages(provider, "gpt-5.3-codex high") is False


def test_normalize_model_name_keeps_responses_quality_suffix():
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
    provider = llm_provider(cfg)
    assert normalize_model_name(provider, "gpt-5.3-codex high") == "gpt-5.3-codex high"


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
