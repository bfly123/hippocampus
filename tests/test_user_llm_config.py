from pathlib import Path

import yaml

from hippocampus.user_llm_config import (
    HIPPOCAMPUS_LLM_CONFIG_NAME,
    build_user_llm_config,
    hippocampus_user_config_dir,
    load_user_llm_config,
    resolve_user_llm_config_file,
    write_user_llm_config,
)


def _write_gateway_user_config(
    tmp_path: Path,
    monkeypatch,
    *,
    base_url: str = "https://backend.example/v1",
    api_key: str = "secret-key",
    max_concurrent: int = 12,
) -> Path:
    cfg_path = tmp_path / ".llmgateway-user" / "config.yaml"
    monkeypatch.setenv("LLMGATEWAY_USER_CONFIG_DIR", str(cfg_path.parent))
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "provider": {
                    "provider_type": "glm",
                    "api_style": "openai_responses",
                    "base_url": base_url,
                    "api_key": api_key,
                    "headers": {},
                    "model_map": {},
                },
                "settings": {
                    "strong_model": "openai/gpt-4.1",
                    "weak_model": "openai/gpt-4o-mini",
                    "strong_reasoning_effort": "high",
                    "weak_reasoning_effort": "low",
                    "max_concurrent": max_concurrent,
                    "retry_max": 3,
                    "timeout": 90,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return cfg_path


def test_user_config_dir_env_override(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HIPPOCAMPUS_USER_CONFIG_DIR", str(tmp_path / "global"))
    assert hippocampus_user_config_dir() == (tmp_path / "global").resolve()


def test_resolve_user_llm_config_file_uses_user_dir(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HIPPOCAMPUS_USER_CONFIG_DIR", str(tmp_path / "global"))
    assert resolve_user_llm_config_file() == (
        tmp_path / "global" / HIPPOCAMPUS_LLM_CONFIG_NAME
    ).resolve()


def test_write_and_load_user_llm_config(tmp_path: Path, monkeypatch):
    _write_gateway_user_config(tmp_path, monkeypatch)
    cfg_path = tmp_path / HIPPOCAMPUS_LLM_CONFIG_NAME
    write_user_llm_config(
        cfg_path,
        model="openai/gpt-4o-mini",
        strong_model="openai/gpt-4.1",
        weak_reasoning_effort="low",
        strong_reasoning_effort="high",
    )
    raw_text = cfg_path.read_text(encoding="utf-8")
    assert "tasks:" in raw_text
    assert "tiers:" not in raw_text
    assert "providers:" not in raw_text
    assert "settings:" not in raw_text
    assert "secret-key" not in raw_text

    loaded = load_user_llm_config(cfg_path)
    assert loaded["llm"]["base_url"] == "https://backend.example/v1"
    assert loaded["llm"]["api_key"] == "secret-key"
    assert loaded["llm"]["max_concurrent"] == 12
    assert loaded["llm"]["phase_models"]["phase_1"] == "openai/gpt-4o-mini"
    assert loaded["llm"]["phase_models"]["phase_2a"] == "openai/gpt-4.1"
    assert loaded["llm"]["phase_reasoning_effort"]["phase_1"] == "low"
    assert loaded["llm"]["phase_reasoning_effort"]["phase_2a"] == "high"


def test_write_and_load_user_llm_config_with_env_refs(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("hippocampus_llm_main_url", "https://backend.example/v1")
    monkeypatch.setenv("hippocampus_llm_main_api_key", "secret-key")
    gateway_path = tmp_path / ".llmgateway-user" / "config.yaml"
    monkeypatch.setenv("LLMGATEWAY_USER_CONFIG_DIR", str(gateway_path.parent))
    gateway_path.parent.mkdir(parents=True, exist_ok=True)
    gateway_path.write_text(
        """
version: 1
provider:
  provider_type: glm
  api_style: openai_responses
  base_url: ${hippocampus_llm_main_url}
  api_key: ${hippocampus_llm_main_api_key}
settings:
  strong_model: openai/gpt-4.1
  weak_model: openai/gpt-4o-mini
  strong_reasoning_effort: high
  weak_reasoning_effort: low
  max_concurrent: 12
""".strip()
        + "\n",
        encoding="utf-8",
    )
    cfg_path = tmp_path / HIPPOCAMPUS_LLM_CONFIG_NAME
    cfg_path.write_text(
        """
version: 1
tasks:
  phase_1:
    tier: weak
  phase_2a:
    tier: strong
""".strip()
        + "\n",
        encoding="utf-8",
    )

    loaded = load_user_llm_config(cfg_path)
    assert loaded["llm"]["base_url"] == "https://backend.example/v1"
    assert loaded["llm"]["api_key"] == "secret-key"
    assert loaded["llm"]["max_concurrent"] == 12
    assert loaded["llm"]["phase_models"]["phase_1"] == "openai/gpt-4o-mini"
    assert loaded["llm"]["phase_models"]["phase_2a"] == "openai/gpt-4.1"
    assert loaded["llm"]["phase_reasoning_effort"]["phase_1"] == "low"
    assert loaded["llm"]["phase_reasoning_effort"]["phase_2a"] == "high"


def test_build_user_llm_config_sets_generic_tiers():
    payload = build_user_llm_config(
        model="openai/glm-4-flash",
    )
    assert payload["tasks"]["phase_1"]["tier"] == "weak"
    assert payload["tasks"]["phase_2a"]["tier"] == "strong"
    assert "providers" not in payload
    assert "settings" not in payload
    assert "tiers" not in payload


def test_build_user_llm_config_supports_weak_and_strong_models(tmp_path: Path, monkeypatch):
    _write_gateway_user_config(tmp_path, monkeypatch, max_concurrent=32)
    payload = build_user_llm_config(
        model="openai/gpt-4o-mini",
        weak_model="openai/gpt-4o-mini",
        strong_model="openai/gpt-4.1",
        weak_reasoning_effort="low",
        strong_reasoning_effort="high",
    )
    assert payload["tasks"]["phase_1"]["tier"] == "weak"
    assert payload["tasks"]["phase_2a"]["tier"] == "strong"
    cfg_path = tmp_path / HIPPOCAMPUS_LLM_CONFIG_NAME
    cfg_path.write_text(
        yaml.safe_dump(payload, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    loaded = load_user_llm_config(cfg_path)
    assert loaded["llm"]["max_concurrent"] == 32
    assert loaded["llm"]["phase_models"]["phase_1"] == "openai/gpt-4o-mini"
    assert loaded["llm"]["phase_models"]["phase_2a"] == "openai/gpt-4.1"
    assert loaded["llm"]["phase_models"]["phase_3b"] == "openai/gpt-4.1"
    assert loaded["llm"]["phase_reasoning_effort"]["phase_1"] == "low"
    assert loaded["llm"]["phase_reasoning_effort"]["phase_2a"] == "high"
    assert loaded["llm"]["phase_reasoning_effort"]["phase_3b"] == "high"


def test_load_user_llm_config_uses_gateway_model_pair(tmp_path: Path, monkeypatch):
    _write_gateway_user_config(tmp_path, monkeypatch, max_concurrent=16)
    cfg_path = tmp_path / HIPPOCAMPUS_LLM_CONFIG_NAME
    cfg_path.write_text(
        """
version: 1
tasks:
  phase_1:
    tier: weak
  phase_2a:
    tier: strong
""".strip()
        + "\n",
        encoding="utf-8",
    )
    loaded = load_user_llm_config(cfg_path)
    assert loaded["llm"]["max_concurrent"] == 16
    assert loaded["llm"]["phase_models"]["phase_1"] == "openai/gpt-4o-mini"
    assert loaded["llm"]["phase_models"]["phase_2a"] == "openai/gpt-4.1"
    assert loaded["llm"]["phase_reasoning_effort"]["phase_1"] == "low"
    assert loaded["llm"]["phase_reasoning_effort"]["phase_2a"] == "high"
