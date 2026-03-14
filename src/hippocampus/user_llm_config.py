from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from .constants import DEFAULT_MAX_CONCURRENT

_ENV_REF_RE = re.compile(
    r"^\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?::-?(?P<default>[^}]*))?\}$"
)
_TASK_TIER_DEFAULTS: dict[str, str] = {
    "phase_1": "small",
    "phase_2a": "strong",
    "phase_2b": "small",
    "phase_3a": "small",
    "phase_3b": "strong",
    "architect": "strong",
}


def prefixed_env_value(text: str) -> str | None:
    if text.startswith("env:") and len(text) > 4:
        return str(os.environ.get(text[4:].strip(), "") or "").strip()
    return None


def placeholder_env_value(text: str) -> str | None:
    match = _ENV_REF_RE.match(text)
    if not match:
        return None
    name = str(match.group("name") or "").strip()
    default = str(match.group("default") or "")
    resolved = os.environ.get(name, default)
    return str(resolved or "").strip()


def resolve_env_value(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    prefixed = prefixed_env_value(text)
    if prefixed is not None:
        return prefixed
    placeholder = placeholder_env_value(text)
    return text if placeholder is None else placeholder


def resolve_env_refs(value: Any) -> Any:
    if isinstance(value, str):
        return resolve_env_value(value)
    if isinstance(value, list):
        return [resolve_env_refs(item) for item in value]
    if isinstance(value, dict):
        return {k: resolve_env_refs(v) for k, v in value.items()}
    return value


def load_user_llm_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(loaded, dict):
        return {}
    resolved = resolve_env_refs(loaded)
    if not isinstance(resolved, dict):
        return {}
    if "llm" in resolved:
        return resolved
    llm = _llm_payload_from_tier_config(resolved)
    return {"llm": llm} if llm else {}


def _dict_section(raw: dict[str, Any], key: str) -> dict[str, Any]:
    section = raw.get(key, {})
    return section if isinstance(section, dict) else {}


def _first_candidate(raw: dict[str, Any], tier_name: str) -> dict[str, Any]:
    tiers = _dict_section(raw, "tiers")
    tier = tiers.get(tier_name, {})
    if not isinstance(tier, dict):
        return {}
    candidates = tier.get("candidates", [])
    if not isinstance(candidates, list) or not candidates:
        return {}
    first = candidates[0]
    return first if isinstance(first, dict) else {}


def _candidate_model(raw: dict[str, Any], tier_name: str) -> str:
    first = _first_candidate(raw, tier_name)
    return str(first.get("model", "") or "").strip()


def _candidate_reasoning_effort(raw: dict[str, Any], tier_name: str) -> str:
    first = _first_candidate(raw, tier_name)
    return str(first.get("reasoning_effort", "") or "").strip().lower()


def _model_suffix_reasoning_effort(model: str) -> str:
    text = str(model or "").strip()
    if not text:
        return ""
    match = _ENV_REF_RE.match(text)
    if match:
        return ""
    suffix_match = re.match(
        r"^(?P<base>.+?)(?:\s+|\s*[\(\[]\s*)(?P<tier>minimal|low|medium|high)\s*[\)\]]?$",
        text,
        re.IGNORECASE,
    )
    if not suffix_match:
        return ""
    return str(suffix_match.group("tier") or "").strip().lower()


def _provider_name(raw: dict[str, Any]) -> str:
    for tier_name in ("strong", "small"):
        first = _first_candidate(raw, tier_name)
        provider_name = str(first.get("provider", "") or "").strip()
        if provider_name:
            return provider_name
    return "main"


def _provider_spec(raw: dict[str, Any], provider_name: str) -> dict[str, Any]:
    providers = _dict_section(raw, "providers")
    provider = providers.get(provider_name, {})
    return provider if isinstance(provider, dict) else {}


def _settings_max_concurrent(raw: dict[str, Any]) -> int:
    settings = _dict_section(raw, "settings")
    value = settings.get("max_concurrent", DEFAULT_MAX_CONCURRENT)
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return DEFAULT_MAX_CONCURRENT


def _task_tier(raw: dict[str, Any], task_name: str, default_tier: str) -> str:
    tasks = _dict_section(raw, "tasks")
    task = tasks.get(task_name, {})
    if not isinstance(task, dict):
        return default_tier
    tier = str(task.get("tier", "") or "").strip()
    return tier or default_tier


def _phase_models_from_tiers(raw: dict[str, Any]) -> dict[str, str]:
    small_model = _candidate_model(raw, "small")
    strong_model = _candidate_model(raw, "strong")
    fallback_model = small_model or strong_model
    phase_models: dict[str, str] = {}
    for task_name, default_tier in _TASK_TIER_DEFAULTS.items():
        tier_name = _task_tier(raw, task_name, default_tier)
        model = _candidate_model(raw, tier_name)
        if not model and tier_name != default_tier:
            model = _candidate_model(raw, default_tier)
        if not model:
            model = strong_model if tier_name == "strong" else small_model
        phase_models[task_name] = model or fallback_model
    return phase_models


def _phase_reasoning_effort_from_tiers(raw: dict[str, Any]) -> dict[str, str]:
    phase_effort: dict[str, str] = {}
    for task_name, default_tier in _TASK_TIER_DEFAULTS.items():
        tier_name = _task_tier(raw, task_name, default_tier)
        effort = _candidate_reasoning_effort(raw, tier_name)
        if not effort:
            effort = _model_suffix_reasoning_effort(_candidate_model(raw, tier_name))
        phase_effort[task_name] = effort
    return phase_effort


def _llm_payload_from_tier_config(raw: dict[str, Any]) -> dict[str, Any]:
    provider = _provider_spec(raw, _provider_name(raw))
    phase_models = _phase_models_from_tiers(raw)
    phase_reasoning_effort = _phase_reasoning_effort_from_tiers(raw)
    fallback_model = (
        phase_models.get("phase_1", "")
        or _candidate_model(raw, "small")
        or _candidate_model(raw, "strong")
    )
    headers = provider.get("headers", {})
    model_map = provider.get("model_map", {})
    return {
        "provider_type": str(provider.get("provider_type", "") or "glm").strip() or "glm",
        "api_style": str(provider.get("api_style", "") or "openai_responses").strip()
        or "openai_responses",
        "max_concurrent": _settings_max_concurrent(raw),
        "base_url": str(provider.get("base_url", "") or "").strip(),
        "api_base": str(provider.get("base_url", "") or "").strip(),
        "api_key": str(provider.get("api_key", "") or "").strip(),
        "extra_headers": dict(headers) if isinstance(headers, dict) else {},
        "model_map": dict(model_map) if isinstance(model_map, dict) else {},
        "fallback_model": fallback_model,
        "phase_models": phase_models,
        "phase_reasoning_effort": phase_reasoning_effort,
    }


def build_user_llm_config(
    *,
    base_url: str,
    api_key: str,
    model: str,
    small_model: str | None = None,
    strong_model: str | None = None,
    small_reasoning_effort: str = "",
    strong_reasoning_effort: str = "",
    provider_type: str = "glm",
    api_style: str = "openai_responses",
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    extra_headers: dict[str, str] | None = None,
    model_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    default_model = str(model).strip()
    small = str(small_model or default_model).strip() or default_model
    strong = str(strong_model or small or default_model).strip() or small or default_model
    return {
        "version": 1,
        "settings": {
            "max_concurrent": max(1, int(max_concurrent)),
        },
        "providers": {
            "main": {
                "provider_type": str(provider_type).strip() or "glm",
                "api_style": str(api_style).strip() or "openai_responses",
                "base_url": str(base_url).strip(),
                "api_key": str(api_key).strip(),
                "headers": dict(extra_headers or {}),
                "model_map": dict(model_map or {}),
            }
        },
        "tiers": {
            "strong": {
                "candidates": [
                    {
                        "provider": "main",
                        "model": strong,
                        **({"reasoning_effort": str(strong_reasoning_effort).strip().lower()} if str(strong_reasoning_effort).strip() else {}),
                    }
                ]
            },
            "small": {
                "candidates": [
                    {
                        "provider": "main",
                        "model": small,
                        **({"reasoning_effort": str(small_reasoning_effort).strip().lower()} if str(small_reasoning_effort).strip() else {}),
                    }
                ]
            },
        },
        "tasks": {
            task_name: {"tier": tier_name}
            for task_name, tier_name in _TASK_TIER_DEFAULTS.items()
        },
    }


def write_user_llm_config(
    path: Path,
    *,
    base_url: str,
    api_key: str,
    model: str,
    small_model: str | None = None,
    strong_model: str | None = None,
    small_reasoning_effort: str = "",
    strong_reasoning_effort: str = "",
    provider_type: str = "glm",
    api_style: str = "openai_responses",
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    extra_headers: dict[str, str] | None = None,
    model_map: dict[str, str] | None = None,
) -> None:
    payload = build_user_llm_config(
        base_url=base_url,
        api_key=api_key,
        model=model,
        small_model=small_model,
        strong_model=strong_model,
        small_reasoning_effort=small_reasoning_effort,
        strong_reasoning_effort=strong_reasoning_effort,
        provider_type=provider_type,
        api_style=api_style,
        max_concurrent=max_concurrent,
        extra_headers=extra_headers,
        model_map=model_map,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


__all__ = [
    "build_user_llm_config",
    "load_user_llm_config",
    "resolve_env_refs",
    "resolve_env_value",
    "write_user_llm_config",
]
