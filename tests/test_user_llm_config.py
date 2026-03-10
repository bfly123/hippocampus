from pathlib import Path

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
    )
    loaded = load_user_llm_config(cfg_path)
    assert loaded["llm"]["base_url"] == "https://backend.example/v1"
    assert loaded["llm"]["api_key"] == "secret-key"
    assert loaded["llm"]["phase_models"]["phase_1"] == "openai/gpt-4o-mini"


def test_build_user_llm_config_sets_all_phases():
    payload = build_user_llm_config(
        base_url="https://backend.example/v1",
        api_key="secret-key",
        model="openai/glm-4-flash",
    )
    assert payload["llm"]["fallback_model"] == "openai/glm-4-flash"
    assert payload["llm"]["phase_models"]["architect"] == "openai/glm-4-flash"


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
