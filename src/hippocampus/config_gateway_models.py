"""Gateway model and route-default helpers for config loading."""

from __future__ import annotations

from typing import Any

from .config_merge_support import (
    is_empty_config_value,
    normalize_str,
    normalize_str_dict,
)


def llm_route_explicit(llm_raw: dict[str, Any]) -> bool:
    return bool(
        normalize_str(llm_raw.get("base_url"))
        or normalize_str(llm_raw.get("api_base"))
        or normalize_str(llm_raw.get("api_key"))
        or normalize_str_dict(llm_raw.get("extra_headers"))
    )


def llm_model_explicit(
    llm_raw: dict[str, Any],
    *,
    default_fallback_model: str,
    default_phase_models: dict[str, str],
) -> bool:
    fallback_raw = normalize_str(llm_raw.get("fallback_model"))
    fallback_explicit = bool(fallback_raw and fallback_raw != default_fallback_model)
    phase_models_raw = llm_raw.get("phase_models")
    phase_models_explicit = (
        isinstance(phase_models_raw, dict)
        and phase_models_raw != default_phase_models
    )
    return fallback_explicit or phase_models_explicit


def set_if_present(obj: Any, attr: str, value: Any) -> None:
    if is_empty_config_value(value):
        return
    setattr(obj, attr, value)


def infer_litellm_provider(model_name: str) -> str | None:
    model_probe = normalize_str(model_name).lower()
    if model_probe.startswith("claude"):
        return "anthropic"
    if model_probe.startswith(("gpt", "o1", "o3", "o4")):
        return "openai"
    return None


def apply_gateway_route_defaults(cfg, profile: dict[str, Any]) -> None:
    base_url = normalize_str(profile.get("base_url"))
    if base_url:
        cfg.llm.base_url = base_url
        cfg.llm.api_base = base_url
    for attr, raw_value, normalize in (
        ("api_key", profile.get("api_key"), normalize_str),
        ("extra_headers", profile.get("extra_headers"), normalize_str_dict),
        ("provider_type", profile.get("provider_type"), normalize_str),
        ("api_style", profile.get("api_style"), normalize_str),
        ("model_map", profile.get("model_map"), normalize_str_dict),
    ):
        set_if_present(cfg.llm, attr, normalize(raw_value))
    if cfg.llm.litellm_provider:
        return
    provider = infer_litellm_provider(str(profile.get("model", "")))
    if provider:
        cfg.llm.litellm_provider = provider


def resolved_gateway_task_models(
    profile: dict[str, Any],
    *,
    backend_model: str,
) -> dict[str, str]:
    task_models = profile.get("task_models", {})
    if not isinstance(task_models, dict):
        task_models = {}
    analyst = normalize_str(task_models.get("context_analyst")) or backend_model
    merger = normalize_str(task_models.get("context_merger")) or analyst or backend_model
    default = backend_model or analyst or merger
    if not default:
        return {}
    return {
        "phase_1": analyst or default,
        "phase_2a": default,
        "phase_2b": analyst or default,
        "phase_3a": merger or default,
        "phase_3b": default,
        "architect": default,
    }
