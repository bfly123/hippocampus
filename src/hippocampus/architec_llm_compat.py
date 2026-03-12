from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml


ARCHITEC_LLM_CONFIG_NAME = "architec-llm.yaml"
_ENV_REF_RE = re.compile(
    r"^\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?::-?(?P<default>[^}]*))?\}$"
)


def architec_user_config_dir() -> Path:
    override = str(os.environ.get("ARCHITEC_USER_CONFIG_DIR", "") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".architec").resolve()


def resolve_architec_llm_config_file(project_root: str | Path | None = None) -> Path:
    if project_root is not None:
        local_override = Path(project_root).resolve() / ".architec" / ARCHITEC_LLM_CONFIG_NAME
        if local_override.exists():
            return local_override
    return architec_user_config_dir() / ARCHITEC_LLM_CONFIG_NAME


def _resolve_env_value(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    env_ref = _env_prefixed_value(text)
    if env_ref is not None:
        return env_ref
    match = _ENV_REF_RE.match(text)
    if not match:
        return text
    name = str(match.group("name") or "").strip()
    default = str(match.group("default") or "")
    return str(os.environ.get(name, default) or "").strip()


def _env_prefixed_value(text: str) -> str | None:
    if text.startswith("env:") and len(text) > 4:
        return str(os.environ.get(text[4:].strip(), "") or "").strip()
    return None


def _resolve_env_refs(value: Any) -> Any:
    if isinstance(value, str):
        return _resolve_env_value(value)
    if isinstance(value, list):
        return [_resolve_env_refs(item) for item in value]
    if isinstance(value, dict):
        return {key: _resolve_env_refs(item) for key, item in value.items()}
    return value


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _first_tier_candidate(raw: dict[str, Any], tier_name: str) -> dict[str, Any] | None:
    tiers = raw.get("tiers", {})
    if not isinstance(tiers, dict):
        return None
    tier = tiers.get(tier_name, {})
    if not isinstance(tier, dict):
        return None
    candidates = tier.get("candidates", [])
    if not isinstance(candidates, list) or not candidates:
        return None
    first = candidates[0]
    return first if isinstance(first, dict) else None


def _candidate_field(raw: dict[str, Any], tier_name: str, field: str) -> str:
    first = _first_tier_candidate(raw, tier_name)
    if not isinstance(first, dict):
        return ""
    return str(first.get(field, "") or "").strip()


def _provider_spec(raw: dict[str, Any], provider_name: str) -> dict[str, Any]:
    providers = raw.get("providers", {})
    if not isinstance(providers, dict):
        return {}
    provider = providers.get(provider_name, {})
    return provider if isinstance(provider, dict) else {}


def _provider_headers(provider: dict[str, Any]) -> dict[str, Any]:
    headers = provider.get("headers", {})
    return headers if isinstance(headers, dict) else {}


def _provider_model_map(provider: dict[str, Any]) -> dict[str, Any]:
    model_map = provider.get("model_map", {})
    return model_map if isinstance(model_map, dict) else {}


def _resolve_provider(raw: dict[str, Any]) -> dict[str, Any]:
    provider_name = (
        _candidate_field(raw, "strong", "provider")
        or _candidate_field(raw, "small", "provider")
        or "main"
    )
    provider = _provider_spec(raw, provider_name)
    return provider if provider else _provider_spec(raw, "main")


def _resolve_fallback_model(
    provider: dict[str, Any],
    strong_model: str,
    small_model: str,
) -> str:
    model = strong_model or small_model
    model_map = _provider_model_map(provider)
    if not model and model_map:
        model = str(next(iter(model_map.values())) or "").strip()
    return model


def _phase_models_payload(strong_model: str, small_model: str, model: str) -> dict[str, str]:
    strong = strong_model or model
    small = small_model or model
    return {
        "phase_1": small,
        "phase_2a": strong,
        "phase_2b": small,
        "phase_3a": strong,
        "phase_3b": strong,
        "architect": strong,
    }


def _llm_payload(
    provider: dict[str, Any],
    *,
    strong_model: str,
    small_model: str,
    fallback_model: str,
) -> dict[str, Any]:
    base_url = str(provider.get("base_url", "") or "").strip()
    api_key = str(provider.get("api_key", "") or "").strip()
    if not (base_url and api_key and fallback_model):
        return {}
    return {
        "provider_type": str(provider.get("provider_type", "") or "glm").strip() or "glm",
        "api_style": str(provider.get("api_style", "") or "openai_responses").strip()
        or "openai_responses",
        "base_url": base_url,
        "api_base": base_url,
        "api_key": api_key,
        "max_concurrent": 4,
        "retry_max": 3,
        "timeout": 120,
        "extra_headers": _provider_headers(provider),
        "model_map": _provider_model_map(provider),
        "fallback_model": fallback_model,
        "phase_models": _phase_models_payload(strong_model, small_model, fallback_model),
    }


def load_architec_llm_as_hippo(path: Path) -> dict[str, Any]:
    raw = _resolve_env_refs(_load_yaml_dict(path))
    if not raw:
        return {}

    strong_model = _candidate_field(raw, "strong", "model")
    small_model = _candidate_field(raw, "small", "model")
    provider = _resolve_provider(raw)
    if not provider:
        return {}

    llm = _llm_payload(
        provider,
        strong_model=strong_model,
        small_model=small_model,
        fallback_model=_resolve_fallback_model(provider, strong_model, small_model),
    )
    return {"llm": llm} if llm else {}


__all__ = [
    "ARCHITEC_LLM_CONFIG_NAME",
    "architec_user_config_dir",
    "load_architec_llm_as_hippo",
    "resolve_architec_llm_config_file",
]
