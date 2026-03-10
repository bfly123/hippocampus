"""YAML configuration loading with Pydantic validation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

from .constants import (
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_RETRY_MAX,
    DEFAULT_TIMEOUT,
)


class LLMPhaseModels(BaseModel):
    phase_1: str = "anthropic/claude-haiku-4-5-20251001"
    phase_2a: str = "anthropic/claude-sonnet-4-5-20250929"
    phase_2b: str = "anthropic/claude-haiku-4-5-20251001"
    phase_3a: str = "anthropic/claude-haiku-4-5-20251001"
    phase_3b: str = "anthropic/claude-sonnet-4-5-20250929"
    architect: str = "anthropic/claude-sonnet-4-5-20250929"


class LLMTemperature(BaseModel):
    phase_1: float = 0.0
    phase_2a: float = 0.0
    phase_2b: float = 0.0
    phase_3a: float = 0.2
    phase_3b: float = 0.3
    architect: float = 0.3


class LLMConfig(BaseModel):
    phase_models: LLMPhaseModels = Field(default_factory=LLMPhaseModels)
    max_concurrent: int = DEFAULT_MAX_CONCURRENT
    retry_max: int = DEFAULT_RETRY_MAX
    timeout: int = DEFAULT_TIMEOUT
    temperature: LLMTemperature = Field(default_factory=LLMTemperature)
    fallback_model: str = "anthropic/claude-haiku-4-5-20251001"
    litellm_provider: Optional[str] = None
    base_url: Optional[str] = None
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    extra_headers: dict[str, str] = Field(default_factory=dict)
    auto_from_llm_gateway: bool = True
    gateway_config_path: Optional[str] = None
    use_backend_task_models: bool = True


class HippoConfig(BaseModel):
    target: str = "."
    output_dir: str = ".hippocampus"
    llm: LLMConfig = Field(default_factory=LLMConfig)
    trim_budget: int = 10000
    structure_prompt_profile: str = "auto"
    structure_prompt_map_tokens: int = 5000
    structure_prompt_deep_tokens: int = 16000
    structure_prompt_max_tokens: int = 10000
    structure_prompt_max_chars: int = 10000  # deprecated, use structure_prompt_max_tokens
    structure_prompt_llm_enhance: bool = False
    structure_prompt_archetype: Optional[str] = None


def _normalize_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _normalize_str_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in value.items():
        kk = _normalize_str(k)
        vv = _normalize_str(v)
        if kk and vv:
            out[kk] = vv
    return out


def _discover_gateway_config(start: Path, explicit_path: str | None) -> Path | None:
    """Find .llmgateway.yaml with monorepo-friendly fallbacks."""
    if explicit_path:
        p = Path(explicit_path).expanduser().resolve()
        if p.is_file():
            return p

    env_path = _normalize_str(
        os.environ.get("LLMGATEWAY_CONFIG")
        or os.environ.get("LLMPROXY_GATEWAY_CONFIG")
    )
    if env_path:
        p = Path(env_path).expanduser().resolve()
        if p.is_file():
            return p

    for d in [start.resolve(), *start.resolve().parents]:
        candidate = d / ".llmgateway.yaml"
        if candidate.is_file():
            return candidate
        monorepo_candidate = d / "llm-proxy" / ".llmgateway.yaml"
        if monorepo_candidate.is_file():
            return monorepo_candidate

    return None


def _load_gateway_backend_profile(path: Path) -> dict[str, Any] | None:
    """Load backend_llm + provider credentials from .llmgateway.yaml."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None

    if not isinstance(raw, dict):
        return None

    backend_llm = raw.get("backend_llm")
    providers = raw.get("providers")
    if not isinstance(backend_llm, dict) or not isinstance(providers, dict):
        return None

    provider_name = _normalize_str(backend_llm.get("provider"))
    provider_cfg = providers.get(provider_name) if provider_name else {}
    if not isinstance(provider_cfg, dict):
        provider_cfg = {}

    return {
        "base_url": _normalize_str(provider_cfg.get("base_url")),
        "api_key": _normalize_str(provider_cfg.get("api_key")),
        "extra_headers": _normalize_str_dict(provider_cfg.get("headers")),
        "model": _normalize_str(backend_llm.get("model")),
        "task_models": _normalize_str_dict(backend_llm.get("task_models")),
    }


def _apply_gateway_llm_defaults(cfg: HippoConfig, raw: dict[str, Any], cfg_path: Path) -> None:
    """Auto-bind hippo LLM settings from llm-proxy backend_llm when not explicit."""
    llm_raw = raw.get("llm") if isinstance(raw.get("llm"), dict) else {}
    assert isinstance(llm_raw, dict)

    if not cfg.llm.auto_from_llm_gateway:
        return

    route_explicit = bool(
        _normalize_str(llm_raw.get("base_url"))
        or _normalize_str(llm_raw.get("api_base"))
        or _normalize_str(llm_raw.get("api_key"))
        or _normalize_str_dict(llm_raw.get("extra_headers"))
    )

    default_llm = LLMConfig()
    fallback_raw = _normalize_str(llm_raw.get("fallback_model"))
    fallback_explicit = bool(fallback_raw and fallback_raw != default_llm.fallback_model)
    phase_models_raw = llm_raw.get("phase_models")
    phase_models_explicit = (
        isinstance(phase_models_raw, dict)
        and phase_models_raw != default_llm.phase_models.model_dump()
    )
    model_explicit = fallback_explicit or phase_models_explicit

    gw_path = _discover_gateway_config(cfg_path.parent, cfg.llm.gateway_config_path)
    if not gw_path:
        return

    profile = _load_gateway_backend_profile(gw_path)
    if not profile:
        return

    if not route_explicit:
        base_url = profile.get("base_url", "")
        if base_url:
            cfg.llm.base_url = base_url
            # Keep legacy field in sync for compatibility.
            cfg.llm.api_base = base_url
        api_key = profile.get("api_key", "")
        if api_key:
            cfg.llm.api_key = api_key
        headers = profile.get("extra_headers", {})
        if headers:
            cfg.llm.extra_headers = headers
        if not cfg.llm.litellm_provider:
            # Heuristic provider inference for non-prefixed models.
            model_probe = _normalize_str(profile.get("model")).lower()
            if model_probe.startswith("claude"):
                cfg.llm.litellm_provider = "anthropic"
            elif model_probe.startswith(("gpt", "o1", "o3", "o4")):
                cfg.llm.litellm_provider = "openai"

    if model_explicit:
        return

    backend_model = _normalize_str(profile.get("model"))
    if backend_model:
        cfg.llm.fallback_model = backend_model

    if not cfg.llm.use_backend_task_models:
        return

    task_models = profile.get("task_models", {})
    if not isinstance(task_models, dict):
        task_models = {}

    analyst = _normalize_str(task_models.get("context_analyst")) or backend_model
    merger = _normalize_str(task_models.get("context_merger")) or analyst or backend_model
    default = backend_model or analyst or merger
    if not default:
        return

    cfg.llm.phase_models.phase_1 = analyst or default
    cfg.llm.phase_models.phase_2a = default
    cfg.llm.phase_models.phase_2b = analyst or default
    cfg.llm.phase_models.phase_3a = merger or default
    cfg.llm.phase_models.phase_3b = default
    cfg.llm.phase_models.architect = default


def load_config(config_path: Optional[Path] = None) -> HippoConfig:
    """Load config from YAML file, falling back to defaults."""
    if config_path and config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        if "structure_prompt_max_tokens" not in raw and "structure_prompt_max_chars" in raw:
            raw["structure_prompt_max_tokens"] = raw["structure_prompt_max_chars"]
        cfg = HippoConfig(**raw)
        _apply_gateway_llm_defaults(cfg, raw, config_path)
        return cfg
    return HippoConfig()


def default_config_yaml() -> str:
    """Generate default config.yaml content."""
    cfg = HippoConfig()
    data = cfg.model_dump()
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)
