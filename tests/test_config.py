"""Tests for hippocampus.config module."""

from __future__ import annotations

from pathlib import Path

import yaml

from hippocampus.config import (
    HippoConfig,
    LLMConfig,
    LLMPhaseModels,
    LLMTemperature,
    default_config_yaml,
    load_config,
)


class TestDefaultConfigYaml:
    def test_is_valid_yaml(self):
        text = default_config_yaml()
        data = yaml.safe_load(text)
        assert isinstance(data, dict)

    def test_has_required_keys(self):
        text = default_config_yaml()
        data = yaml.safe_load(text)
        assert "target" in data
        assert "output_dir" in data
        assert "llm" in data


class TestLoadConfig:
    def test_load_none_returns_defaults(self):
        cfg = load_config(None)
        assert isinstance(cfg, HippoConfig)
        assert cfg.target == "."
        assert cfg.output_dir == ".hippocampus"

    def test_load_from_file(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump({
            "target": "/some/path",
            "trim_budget": 5000,
        }))
        cfg = load_config(cfg_file)
        assert cfg.target == "/some/path"
        assert cfg.trim_budget == 5000

    def test_load_missing_file_returns_defaults(self, tmp_path):
        cfg = load_config(tmp_path / "nonexistent.yaml")
        assert isinstance(cfg, HippoConfig)

    def test_auto_bind_from_gateway_monorepo_layout(self, tmp_path: Path):
        project = tmp_path / "inner"
        project.mkdir()
        cfg_file = project / ".hippocampus" / "config.yaml"
        cfg_file.parent.mkdir()
        cfg_file.write_text("target: .\n")

        gw_dir = project / "llm-proxy"
        gw_dir.mkdir()
        gw_file = gw_dir / ".llmgateway.yaml"
        gw_file.write_text(
            yaml.dump(
                {
                    "providers": {
                        "right": {
                            "base_url": "https://backend.example/v1",
                            "api_key": "test-key",
                            "headers": {"x-test": "1"},
                        }
                    },
                    "backend_llm": {
                        "provider": "right",
                        "model": "gpt-backend-main",
                        "task_models": {
                            "context_analyst": "gpt-backend-analyst",
                            "context_merger": "gpt-backend-merger",
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        cfg = load_config(cfg_file)
        assert cfg.llm.base_url == "https://backend.example/v1"
        assert cfg.llm.api_base == "https://backend.example/v1"
        assert cfg.llm.api_key == "test-key"
        assert cfg.llm.extra_headers == {"x-test": "1"}
        assert cfg.llm.litellm_provider == "openai"
        assert cfg.llm.fallback_model == "gpt-backend-main"
        assert cfg.llm.phase_models.phase_1 == "gpt-backend-analyst"
        assert cfg.llm.phase_models.phase_3a == "gpt-backend-merger"

    def test_explicit_llm_route_not_overridden(self, tmp_path: Path):
        project = tmp_path / "inner"
        project.mkdir()
        cfg_file = project / ".hippocampus" / "config.yaml"
        cfg_file.parent.mkdir()
        cfg_file.write_text(
            yaml.dump(
                {
                    "llm": {
                        "base_url": "http://manual-base",
                        "api_key": "manual-key",
                    }
                }
            ),
            encoding="utf-8",
        )

        gw_dir = project / "llm-proxy"
        gw_dir.mkdir()
        (gw_dir / ".llmgateway.yaml").write_text(
            yaml.dump(
                {
                    "providers": {"p": {"base_url": "http://gw", "api_key": "gw-key"}},
                    "backend_llm": {"provider": "p", "model": "gw-model"},
                }
            ),
            encoding="utf-8",
        )

        cfg = load_config(cfg_file)
        assert cfg.llm.base_url == "http://manual-base"
        assert cfg.llm.api_key == "manual-key"


class TestHippoConfig:
    def test_defaults(self):
        cfg = HippoConfig()
        assert cfg.trim_budget == 10000
        assert cfg.structure_prompt_max_chars == 10000
        assert cfg.structure_prompt_llm_enhance is False
        assert cfg.structure_prompt_archetype is None

    def test_llm_defaults(self):
        cfg = HippoConfig()
        assert cfg.llm.max_concurrent == 20
        assert cfg.llm.retry_max == 3
        assert cfg.llm.timeout == 30


class TestLLMPhaseModels:
    def test_defaults(self):
        m = LLMPhaseModels()
        assert "haiku" in m.phase_1
        assert "sonnet" in m.phase_2a


class TestLLMTemperature:
    def test_defaults(self):
        t = LLMTemperature()
        assert t.phase_1 == 0.0
        assert t.phase_2a == 0.0
