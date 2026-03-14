from pathlib import Path

import yaml

from hippocampus.resource_paths import (
    HIPPOCAMPUS_LLM_CONFIG_NAME,
    resolve_hippo_llm_config_file,
    user_config_dir,
)
from hippocampus.architec_llm_compat import (
    load_architec_llm_as_hippo,
    resolve_architec_llm_config_file,
)
from hippocampus.user_llm_config import (
    build_user_llm_config,
    load_user_llm_config,
    write_user_llm_config,
)


def test_user_config_dir_env_override(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HIPPOCAMPUS_USER_CONFIG_DIR", str(tmp_path / "global"))
    assert user_config_dir() == (tmp_path / "global").resolve()


def test_resolve_project_override_first(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HIPPOCAMPUS_USER_CONFIG_DIR", str(tmp_path / "global"))
    project = tmp_path / "project"
    project_llm = project / ".hippocampus" / HIPPOCAMPUS_LLM_CONFIG_NAME
    project_llm.parent.mkdir(parents=True)
    project_llm.write_text("llm:\n  api_key: project-key\n", encoding="utf-8")
    assert resolve_hippo_llm_config_file(project) == project_llm


def test_write_and_load_user_llm_config(tmp_path: Path):
    cfg_path = tmp_path / HIPPOCAMPUS_LLM_CONFIG_NAME
    write_user_llm_config(
        cfg_path,
        base_url="https://backend.example/v1",
        api_key="secret-key",
        model="openai/gpt-4o-mini",
        strong_model="openai/gpt-4.1",
        small_reasoning_effort="low",
        strong_reasoning_effort="high",
    )
    raw_text = cfg_path.read_text(encoding="utf-8")
    assert "settings:" in raw_text
    assert "max_concurrent: 20" in raw_text
    assert "providers:" in raw_text
    assert "tiers:" in raw_text
    assert "tasks:" in raw_text
    assert "secret-key" in raw_text

    loaded = load_user_llm_config(cfg_path)
    assert loaded["llm"]["base_url"] == "https://backend.example/v1"
    assert loaded["llm"]["api_key"] == "secret-key"
    assert loaded["llm"]["max_concurrent"] == 20
    assert loaded["llm"]["phase_models"]["phase_1"] == "openai/gpt-4o-mini"
    assert loaded["llm"]["phase_models"]["phase_2a"] == "openai/gpt-4.1"
    assert loaded["llm"]["phase_reasoning_effort"]["phase_1"] == "low"
    assert loaded["llm"]["phase_reasoning_effort"]["phase_2a"] == "high"


def test_write_and_load_user_llm_config_with_env_refs(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("hippocampus_llm_main_url", "https://backend.example/v1")
    monkeypatch.setenv("hippocampus_llm_main_api_key", "secret-key")
    cfg_path = tmp_path / HIPPOCAMPUS_LLM_CONFIG_NAME
    cfg_path.write_text(
        """
version: 1
settings:
  max_concurrent: 12
providers:
  main:
    provider_type: glm
    api_style: openai_responses
    base_url: ${hippocampus_llm_main_url}
    api_key: ${hippocampus_llm_main_api_key}
tiers:
  strong:
    candidates:
      - provider: main
        model: openai/gpt-4.1
        reasoning_effort: high
  small:
    candidates:
      - provider: main
        model: openai/gpt-4o-mini
        reasoning_effort: low
tasks:
  phase_1:
    tier: small
  phase_2a:
    tier: strong
  phase_2b:
    tier: small
  phase_3a:
    tier: small
  phase_3b:
    tier: strong
  architect:
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


def test_build_user_llm_config_sets_all_phases():
    payload = build_user_llm_config(
        base_url="https://backend.example/v1",
        api_key="secret-key",
        model="openai/glm-4-flash",
    )
    assert payload["providers"]["main"]["provider_type"] == "glm"
    assert payload["settings"]["max_concurrent"] == 20
    assert payload["tiers"]["small"]["candidates"][0]["model"] == "openai/glm-4-flash"
    assert payload["tasks"]["architect"]["tier"] == "strong"


def test_build_user_llm_config_supports_small_and_strong_models(tmp_path: Path):
    payload = build_user_llm_config(
        base_url="https://backend.example/v1",
        api_key="secret-key",
        model="openai/gpt-4o-mini",
        small_model="openai/gpt-4o-mini",
        strong_model="openai/gpt-4.1",
        small_reasoning_effort="low",
        strong_reasoning_effort="high",
        max_concurrent=32,
    )
    assert payload["settings"]["max_concurrent"] == 32
    assert payload["tiers"]["small"]["candidates"][0]["model"] == "openai/gpt-4o-mini"
    assert payload["tiers"]["strong"]["candidates"][0]["model"] == "openai/gpt-4.1"
    assert payload["tiers"]["small"]["candidates"][0]["reasoning_effort"] == "low"
    assert payload["tiers"]["strong"]["candidates"][0]["reasoning_effort"] == "high"
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


def test_load_user_llm_config_infers_reasoning_effort_from_model_suffix(tmp_path: Path):
    cfg_path = tmp_path / HIPPOCAMPUS_LLM_CONFIG_NAME
    cfg_path.write_text(
        """
version: 1
settings:
  max_concurrent: 16
providers:
  main:
    provider_type: glm
    api_style: openai_responses
    base_url: https://backend.example/v1
    api_key: secret-key
tiers:
  strong:
    candidates:
      - provider: main
        model: openai/gpt-5.4 high
  small:
    candidates:
      - provider: main
        model: openai/gpt-5.4 low
tasks:
  phase_1:
    tier: small
  phase_2a:
    tier: strong
  phase_2b:
    tier: small
  phase_3a:
    tier: small
  phase_3b:
    tier: strong
  architect:
    tier: strong
""".strip()
        + "\n",
        encoding="utf-8",
    )
    loaded = load_user_llm_config(cfg_path)
    assert loaded["llm"]["max_concurrent"] == 16
    assert loaded["llm"]["phase_models"]["phase_1"] == "openai/gpt-5.4 low"
    assert loaded["llm"]["phase_models"]["phase_2a"] == "openai/gpt-5.4 high"
    assert loaded["llm"]["phase_reasoning_effort"]["phase_1"] == "low"
    assert loaded["llm"]["phase_reasoning_effort"]["phase_2a"] == "high"


def test_resolve_architec_user_config(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ARCHITEC_USER_CONFIG_DIR", str(tmp_path / "arch-user"))
    assert resolve_architec_llm_config_file() == (tmp_path / "arch-user" / "architec-llm.yaml").resolve()


def test_load_architec_llm_as_hippo(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("architec_llm_main_url", "https://arch.example/v1")
    monkeypatch.setenv("architec_llm_main_api_key", "arch-key")
    cfg_path = tmp_path / "architec-llm.yaml"
    cfg_path.write_text(
        """
providers:
  main:
    base_url: ${architec_llm_main_url}
    api_key: ${architec_llm_main_api_key}
tiers:
  strong:
    candidates:
      - provider: main
        model: gpt-5.3-codex high
  small:
    candidates:
      - provider: main
        model: gpt-5.3-codex-medium
""".strip()
        + "\n",
        encoding="utf-8",
    )
    loaded = load_architec_llm_as_hippo(cfg_path)
    assert loaded["llm"]["base_url"] == "https://arch.example/v1"
    assert loaded["llm"]["api_key"] == "arch-key"
    assert loaded["llm"]["phase_models"]["phase_1"] == "gpt-5.3-codex-medium"
    assert loaded["llm"]["phase_models"]["architect"] == "gpt-5.3-codex high"
