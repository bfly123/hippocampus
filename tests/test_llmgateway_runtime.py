from __future__ import annotations

from pathlib import Path

import yaml

from hippocampus.integration.llmgateway_runtime import (
    describe_user_gateway_runtime_issue,
    load_user_gateway_runtime_profile,
    resolve_user_gateway_runtime_file,
)


def test_resolve_user_gateway_runtime_file_uses_env_dir(monkeypatch, tmp_path: Path) -> None:
    user_dir = tmp_path / "gateway-user"
    monkeypatch.setenv("LLMGATEWAY_USER_CONFIG_DIR", str(user_dir))

    resolved = resolve_user_gateway_runtime_file()

    assert resolved == (user_dir / "config.yaml").resolve()


def test_load_user_gateway_runtime_profile_uses_user_config_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    user_dir = tmp_path / "gateway-user"
    monkeypatch.setenv("LLMGATEWAY_USER_CONFIG_DIR", str(user_dir))
    cfg_path = user_dir / "config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "provider": {
                    "provider_type": "glm",
                    "api_style": "openai_responses",
                    "base_url": "https://backend.example/v1",
                    "api_key": "secret-key",
                    "headers": {"x-test": "1"},
                    "model_map": {"default": "gpt-5.4"},
                },
                "settings": {
                    "strong_model": "gpt-5.4",
                    "weak_model": "gpt-5.4-mini",
                    "strong_reasoning_effort": "high",
                    "weak_reasoning_effort": "low",
                    "max_concurrent": 12,
                    "retry_max": 3,
                    "timeout": 90,
                    "transport_retries": 4,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    profile = load_user_gateway_runtime_profile()

    assert profile["provider_type"] == "glm"
    assert profile["api_style"] == "openai_responses"
    assert profile["base_url"] == "https://backend.example/v1"
    assert profile["api_key"] == "secret-key"
    assert profile["extra_headers"] == {"x-test": "1"}
    assert profile["model_map"] == {"default": "gpt-5.4"}
    assert profile["strong_model"] == "gpt-5.4"
    assert profile["weak_model"] == "gpt-5.4-mini"
    assert profile["strong_reasoning_effort"] == "high"
    assert profile["weak_reasoning_effort"] == "low"
    assert profile["max_concurrent"] == 12
    assert profile["retry_max"] == 3
    assert profile["timeout"] == 90.0
    assert profile["transport_retries"] == 4


def test_describe_user_gateway_runtime_issue_reports_yaml_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    user_dir = tmp_path / "gateway-user"
    monkeypatch.setenv("LLMGATEWAY_USER_CONFIG_DIR", str(user_dir))
    cfg_path = user_dir / "config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text("provider: [\n", encoding="utf-8")

    issue = describe_user_gateway_runtime_issue()

    assert issue is not None
    assert str(cfg_path) in issue
    assert "cannot be parsed" in issue


def test_describe_user_gateway_runtime_issue_reports_missing_required_fields(
    monkeypatch,
    tmp_path: Path,
) -> None:
    user_dir = tmp_path / "gateway-user"
    monkeypatch.setenv("LLMGATEWAY_USER_CONFIG_DIR", str(user_dir))
    cfg_path = user_dir / "config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "provider": {
                    "provider_type": "openai",
                    "api_style": "responses",
                    "base_url": "https://backend.example/v1",
                },
                "settings": {},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    issue = describe_user_gateway_runtime_issue()

    assert issue is not None
    assert "provider.api_key" in issue
    assert "settings.strong_model / settings.weak_model / settings.fallback_model" in issue
