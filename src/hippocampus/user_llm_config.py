from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from llmgateway.config import (
    resolve_env_refs,
    resolve_env_value,
)

from .constants import DEFAULT_MAX_CONCURRENT
from .integration.llmgateway_runtime import load_user_gateway_runtime_profile

HIPPOCAMPUS_LLM_CONFIG_NAME = "config.yaml"

_TASK_TIER_DEFAULTS: dict[str, str] = {
    "phase_1": "weak",
    "phase_2a": "strong",
    "phase_2b": "weak",
    "phase_3a": "weak",
    "phase_3b": "strong",
    "architect": "strong",
}


def _compact_error(exc: Exception) -> str:
    return " ".join(str(exc).split())


def hippocampus_user_config_dir() -> Path:
    override = str(os.environ.get("HIPPOCAMPUS_USER_CONFIG_DIR", "") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".hippocampus").resolve()


def resolve_user_llm_config_file(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path).expanduser().resolve()
    explicit = str(os.environ.get("HIPPOCAMPUS_LLM_CONFIG", "") or "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    return hippocampus_user_config_dir() / HIPPOCAMPUS_LLM_CONFIG_NAME


def load_user_llm_config(path: Path | None = None) -> dict[str, Any]:
    resolved = _load_yaml_dict(resolve_user_llm_config_file(path))
    resolved = resolve_env_refs(resolved)
    if not isinstance(resolved, dict) or not resolved:
        return {}
    llm = _llm_payload_from_tasks_config(resolved)
    return {"llm": llm} if llm else {}


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _dict_section(raw: dict[str, Any], key: str) -> dict[str, Any]:
    section = raw.get(key, {})
    return section if isinstance(section, dict) else {}


def _task_tier(raw: dict[str, Any], task_name: str, default_tier: str) -> str:
    tasks = _dict_section(raw, "tasks")
    task = tasks.get(task_name, {})
    if not isinstance(task, dict):
        return default_tier
    tier = str(task.get("tier", "") or "").strip()
    return tier or default_tier


def _phase_tiers_from_tasks(raw: dict[str, Any]) -> dict[str, str]:
    phase_tiers: dict[str, str] = {}
    for task_name, default_tier in _TASK_TIER_DEFAULTS.items():
        phase_tiers[task_name] = _task_tier(raw, task_name, default_tier)
    return phase_tiers


def _phase_models_payload(
    phase_tiers: dict[str, str],
    *,
    strong_model: str,
    weak_model: str,
    fallback_model: str,
) -> dict[str, str]:
    phase_models: dict[str, str] = {}
    for task_name, default_tier in _TASK_TIER_DEFAULTS.items():
        tier_name = str(phase_tiers.get(task_name, "") or default_tier).strip().lower()
        if tier_name == "strong":
            phase_models[task_name] = strong_model or weak_model or fallback_model
        else:
            phase_models[task_name] = weak_model or strong_model or fallback_model
    return phase_models


def _phase_reasoning_effort_payload(
    phase_tiers: dict[str, str],
    *,
    strong_reasoning_effort: str,
    weak_reasoning_effort: str,
) -> dict[str, str]:
    phase_effort: dict[str, str] = {}
    for task_name, default_tier in _TASK_TIER_DEFAULTS.items():
        tier_name = str(phase_tiers.get(task_name, "") or default_tier).strip().lower()
        phase_effort[task_name] = (
            strong_reasoning_effort if tier_name == "strong" else weak_reasoning_effort
        )
    return phase_effort


def _llm_payload_from_tasks_config(raw: dict[str, Any]) -> dict[str, Any]:
    route = load_user_gateway_runtime_profile()
    strong_model = str(route.get("strong_model", "") or "").strip()
    weak_model = str(route.get("weak_model", "") or strong_model or "").strip()
    strong_reasoning_effort = str(route.get("strong_reasoning_effort", "") or "").strip().lower()
    weak_reasoning_effort = str(route.get("weak_reasoning_effort", "") or "").strip().lower()
    phase_tiers = _phase_tiers_from_tasks(raw)
    fallback_model = weak_model or strong_model or str(route.get("fallback_model", "") or "").strip()
    phase_models = _phase_models_payload(
        phase_tiers,
        strong_model=strong_model,
        weak_model=weak_model,
        fallback_model=fallback_model,
    )
    phase_reasoning_effort = _phase_reasoning_effort_payload(
        phase_tiers,
        strong_reasoning_effort=strong_reasoning_effort,
        weak_reasoning_effort=weak_reasoning_effort,
    )
    return {
        "provider_type": str(route.get("provider_type", "") or "glm").strip() or "glm",
        "api_style": str(route.get("api_style", "") or "openai_responses").strip()
        or "openai_responses",
        "max_concurrent": max(1, int(route.get("max_concurrent", DEFAULT_MAX_CONCURRENT) or DEFAULT_MAX_CONCURRENT)),
        "retry_max": max(0, int(route.get("retry_max", 3) or 3)),
        "timeout": float(route.get("timeout", 30) or 30),
        "base_url": str(route.get("base_url", "") or "").strip(),
        "api_base": str(route.get("base_url", "") or "").strip(),
        "api_key": str(route.get("api_key", "") or "").strip(),
        "extra_headers": dict(route.get("extra_headers", {}) or {}),
        "model_map": dict(route.get("model_map", {}) or {}),
        "strong_model": strong_model,
        "weak_model": weak_model,
        "strong_reasoning_effort": strong_reasoning_effort,
        "weak_reasoning_effort": weak_reasoning_effort,
        "fallback_model": fallback_model,
        "phase_tiers": phase_tiers,
        "phase_models": phase_models,
        "phase_reasoning_effort": phase_reasoning_effort,
    }


def describe_user_llm_config_issue(path: Path | None = None) -> str | None:
    resolved_path = resolve_user_llm_config_file(path)
    if not resolved_path.exists():
        return None
    try:
        loaded = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"{resolved_path} cannot be parsed: {_compact_error(exc)}"
    if loaded is None:
        return f"{resolved_path} is empty."
    if not isinstance(loaded, dict):
        return f"{resolved_path} must contain a YAML object at the top level."
    try:
        resolved = resolve_env_refs(loaded)
    except Exception as exc:
        return f"{resolved_path} contains invalid environment references: {_compact_error(exc)}"
    if not isinstance(resolved, dict):
        return f"{resolved_path} must resolve to a YAML object."
    tasks = resolved.get("tasks")
    if tasks is not None and not isinstance(tasks, dict):
        return f"{resolved_path} field 'tasks' must be an object."
    return None


def build_user_llm_config(
    *,
    model: str,
    weak_model: str | None = None,
    strong_model: str | None = None,
    weak_reasoning_effort: str = "",
    strong_reasoning_effort: str = "",
) -> dict[str, Any]:
    return {
        "version": 1,
        "tasks": {
            task_name: {"tier": tier_name}
            for task_name, tier_name in _TASK_TIER_DEFAULTS.items()
        },
    }


def write_user_llm_config(
    path: Path,
    *,
    model: str,
    weak_model: str | None = None,
    strong_model: str | None = None,
    weak_reasoning_effort: str = "",
    strong_reasoning_effort: str = "",
) -> None:
    payload = build_user_llm_config(
        model=model,
        weak_model=weak_model,
        strong_model=strong_model,
        weak_reasoning_effort=weak_reasoning_effort,
        strong_reasoning_effort=strong_reasoning_effort,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


__all__ = [
    "HIPPOCAMPUS_LLM_CONFIG_NAME",
    "build_user_llm_config",
    "describe_user_llm_config_issue",
    "hippocampus_user_config_dir",
    "load_user_llm_config",
    "resolve_env_refs",
    "resolve_env_value",
    "resolve_user_llm_config_file",
    "write_user_llm_config",
]
