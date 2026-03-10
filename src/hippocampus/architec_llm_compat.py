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
    if text.startswith("env:") and len(text) > 4:
        return str(os.environ.get(text[4:].strip(), "") or "").strip()
    match = _ENV_REF_RE.match(text)
    if not match:
        return text
    name = str(match.group("name") or "").strip()
    default = str(match.group("default") or "")
    return str(os.environ.get(name, default) or "").strip()


def _resolve_env_refs(value: Any) -> Any:
    if isinstance(value, str):
        return _resolve_env_value(value)
    if isinstance(value, list):
        return [_resolve_env_refs(item) for item in value]
    if isinstance(value, dict):
        return {k: _resolve_env_refs(v) for k, v in value.items()}
    return value


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _candidate_model(raw: dict[str, Any], tier_name: str) -> str:
    tiers = raw.get("tiers", {})
    if not isinstance(tiers, dict):
        return ""
    tier = tiers.get(tier_name, {})
    if not isinstance(tier, dict):
        return ""
    candidates = tier.get("candidates", [])
    if not isinstance(candidates, list) or not candidates:
        return ""
    first = candidates[0]
    if not isinstance(first, dict):
        return ""
    return str(first.get("model", "") or "").strip()


def _provider_spec(raw: dict[str, Any], provider_name: str) -> dict[str, Any]:
    providers = raw.get("providers", {})
    if not isinstance(providers, dict):
        return {}
    provider = providers.get(provider_name, {})
    return provider if isinstance(provider, dict) else {}


def _candidate_provider_name(raw: dict[str, Any], tier_name: str) -> str:
    tiers = raw.get("tiers", {})
    if not isinstance(tiers, dict):
        return ""
    tier = tiers.get(tier_name, {})
    if not isinstance(tier, dict):
        return ""
    candidates = tier.get("candidates", [])
    if not isinstance(candidates, list) or not candidates:
        return ""
    first = candidates[0]
    if not isinstance(first, dict):
        return ""
    return str(first.get("provider", "") or "").strip()


def load_architec_llm_as_hippo(path: Path) -> dict[str, Any]:
    raw = _resolve_env_refs(_load_yaml_dict(path))
    if not raw:
        return {}

    strong_model = _candidate_model(raw, "strong")
    small_model = _candidate_model(raw, "small")
    provider_name = _candidate_provider_name(raw, "strong") or _candidate_provider_name(raw, "small") or "main"
    provider = _provider_spec(raw, provider_name)
    if not provider:
        provider = _provider_spec(raw, "main")
    if not provider:
        return {}

    base_url = str(provider.get("base_url", "") or "").strip()
    api_key = str(provider.get("api_key", "") or "").strip()
    headers = provider.get("headers", {})
    model = strong_model or small_model
    if not model and isinstance(provider.get("model_map"), dict) and provider["model_map"]:
        model = str(next(iter(provider["model_map"].values())) or "").strip()
    if not (base_url and api_key and model):
        return {}

    llm = {
        "provider_type": str(provider.get("provider_type", "") or "glm").strip() or "glm",
        "api_style": str(provider.get("api_style", "") or "openai_responses").strip() or "openai_responses",
        "base_url": base_url,
        "api_base": base_url,
        "api_key": api_key,
        "extra_headers": headers if isinstance(headers, dict) else {},
        "model_map": provider.get("model_map", {}) if isinstance(provider.get("model_map"), dict) else {},
        "fallback_model": model,
        "phase_models": {
            "phase_1": small_model or model,
            "phase_2a": strong_model or model,
            "phase_2b": small_model or model,
            "phase_3a": strong_model or model,
            "phase_3b": strong_model or model,
            "architect": strong_model or model,
        },
    }
    return {"llm": llm}


__all__ = [
    "ARCHITEC_LLM_CONFIG_NAME",
    "architec_user_config_dir",
    "load_architec_llm_as_hippo",
    "resolve_architec_llm_config_file",
]
