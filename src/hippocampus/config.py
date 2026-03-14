"""YAML configuration loading with Pydantic validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

from .constants import (
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_RETRY_MAX,
    DEFAULT_TIMEOUT,
)
from .architec_llm_compat import (
    load_architec_llm_as_hippo,
    resolve_architec_llm_config_file,
)
from .config_gateway_models import (
    apply_gateway_route_defaults,
    llm_model_explicit,
    llm_route_explicit,
    resolved_gateway_task_models,
)
from .config_gateway_support import (
    discover_gateway_config,
    load_gateway_backend_profile,
)
from .config_merge_support import (
    infer_project_root,
    load_yaml_dict,
    merge_dicts,
    merge_dicts_skipping_empty_defaults,
    normalize_str,
)
from .integration.resource_paths import resolve_hippo_llm_config_file
from .user_llm_config import load_user_llm_config


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


class LLMReasoningEffort(BaseModel):
    phase_1: str = ""
    phase_2a: str = ""
    phase_2b: str = ""
    phase_3a: str = ""
    phase_3b: str = ""
    architect: str = ""


class LLMConfig(BaseModel):
    phase_models: LLMPhaseModels = Field(default_factory=LLMPhaseModels)
    phase_reasoning_effort: LLMReasoningEffort = Field(default_factory=LLMReasoningEffort)
    max_concurrent: int = DEFAULT_MAX_CONCURRENT
    retry_max: int = DEFAULT_RETRY_MAX
    timeout: int = DEFAULT_TIMEOUT
    temperature: LLMTemperature = Field(default_factory=LLMTemperature)
    fallback_model: str = "anthropic/claude-haiku-4-5-20251001"
    litellm_provider: Optional[str] = None
    provider_type: Optional[str] = None
    api_style: Optional[str] = None
    base_url: Optional[str] = None
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    extra_headers: dict[str, str] = Field(default_factory=dict)
    model_map: dict[str, str] = Field(default_factory=dict)
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

def _merge_user_llm_config(
    raw: dict[str, Any],
    config_path: Optional[Path],
    project_root: Optional[Path],
) -> dict[str, Any]:
    root = infer_project_root(config_path, project_root)
    llm_cfg_path = resolve_hippo_llm_config_file(root)
    user_raw = load_user_llm_config(llm_cfg_path)
    base_raw = user_raw
    if not base_raw:
        base_raw = load_architec_llm_as_hippo(resolve_architec_llm_config_file(root))
    if not base_raw:
        return raw

    merged = merge_dicts(base_raw, raw)
    base_llm = base_raw.get("llm", {}) if isinstance(base_raw.get("llm"), dict) else {}
    raw_llm = raw.get("llm", {}) if isinstance(raw.get("llm"), dict) else {}
    if base_llm and raw_llm:
        merged["llm"] = merge_dicts_skipping_empty_defaults(
            base_llm,
            raw_llm,
            defaults=LLMConfig().model_dump(),
        )
    return merged


def _apply_gateway_model_defaults(cfg: HippoConfig, profile: dict[str, Any]) -> None:
    backend_model = normalize_str(profile.get("model"))
    if backend_model:
        cfg.llm.fallback_model = backend_model
    if not cfg.llm.use_backend_task_models:
        return
    resolved = resolved_gateway_task_models(profile, backend_model=backend_model)
    for attr, value in resolved.items():
        setattr(cfg.llm.phase_models, attr, value)


def _apply_gateway_llm_defaults(cfg: HippoConfig, raw: dict[str, Any], cfg_path: Path) -> None:
    """Auto-bind hippo LLM settings from llm-proxy backend_llm when not explicit."""
    llm_raw = raw.get("llm") if isinstance(raw.get("llm"), dict) else {}
    assert isinstance(llm_raw, dict)

    if not cfg.llm.auto_from_llm_gateway:
        return

    default_llm = LLMConfig()
    route_explicit = llm_route_explicit(llm_raw)
    model_explicit = llm_model_explicit(
        llm_raw,
        default_fallback_model=default_llm.fallback_model,
        default_phase_models=default_llm.phase_models.model_dump(),
    )

    gw_path = discover_gateway_config(cfg_path.parent, cfg.llm.gateway_config_path)
    if not gw_path:
        return

    profile = load_gateway_backend_profile(gw_path)
    if not profile:
        return

    if not route_explicit:
        apply_gateway_route_defaults(cfg, profile)

    if model_explicit:
        return

    _apply_gateway_model_defaults(cfg, profile)


def _load_config_from_raw(
    raw: dict[str, Any],
    *,
    config_path: Path | None,
    project_root: Optional[Path],
) -> HippoConfig:
    cfg = HippoConfig(**raw)
    if config_path is not None:
        _apply_gateway_llm_defaults(cfg, raw, config_path)
    elif project_root is not None:
        _apply_gateway_llm_defaults(cfg, raw, project_root / ".hippocampus" / "config.yaml")
    return cfg


def load_config(config_path: Optional[Path] = None, *, project_root: Optional[Path] = None) -> HippoConfig:
    """Load config from YAML file, falling back to defaults."""
    if config_path and config_path.exists():
        raw = load_yaml_dict(config_path)
        raw = _merge_user_llm_config(raw, config_path, project_root)
        if "structure_prompt_max_tokens" not in raw and "structure_prompt_max_chars" in raw:
            raw["structure_prompt_max_tokens"] = raw["structure_prompt_max_chars"]
        return _load_config_from_raw(raw, config_path=config_path, project_root=project_root)
    raw = _merge_user_llm_config({}, config_path, project_root)
    if raw:
        return _load_config_from_raw(raw, config_path=None, project_root=project_root)
    return HippoConfig()


def llm_is_configured(cfg: HippoConfig) -> bool:
    llm = cfg.llm
    base_url = normalize_str(llm.base_url or llm.api_base)
    api_key = normalize_str(llm.api_key)
    model = normalize_str(llm.fallback_model)
    return bool(base_url and api_key and model)


def require_llm_configured(cfg: HippoConfig) -> None:
    if llm_is_configured(cfg):
        return
    raise RuntimeError(
        "hippocampus requires LLM configuration. "
        "Set ~/.hippocampus/hippocampus-llm.yaml or ~/.architec/architec-llm.yaml first."
    )


def default_config_yaml() -> str:
    """Generate default config.yaml content."""
    cfg = HippoConfig()
    data = cfg.model_dump()
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)
