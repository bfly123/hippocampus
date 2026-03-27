from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from llmgateway.config import (
    load_user_config as load_gateway_user_config,
    resolve_env_refs,
    runtime_spec_from_dict,
)


def _compact_error(exc: Exception) -> str:
    return " ".join(str(exc).split())


def runtime_profile_from_gateway_raw(raw: dict[str, Any]) -> dict[str, Any]:
    runtime = runtime_spec_from_dict(raw)
    task_models = {
        str(task_name): str(task.model or "").strip()
        for task_name, task in runtime.tasks.items()
        if str(task_name or "").strip() and str(task.model or "").strip()
    }
    return {
        "provider_type": str(runtime.provider.provider_type or "").strip(),
        "api_style": str(runtime.provider.api_style or "").strip(),
        "base_url": str(runtime.provider.base_url or "").strip(),
        "api_key": str(runtime.provider.api_key or "").strip(),
        "extra_headers": dict(runtime.provider.headers or {}),
        "model_map": dict(runtime.provider.model_map or {}),
        "fallback_model": str(runtime.fallback_model or "").strip(),
        "strong_model": str(runtime.strong_model or "").strip(),
        "weak_model": str(runtime.weak_model or "").strip(),
        "strong_reasoning_effort": str(runtime.strong_reasoning_effort or "").strip().lower(),
        "weak_reasoning_effort": str(runtime.weak_reasoning_effort or "").strip().lower(),
        "max_concurrent": max(1, int(runtime.max_concurrent)),
        "retry_max": max(0, int(runtime.retry_max)),
        "timeout": float(runtime.timeout),
        "transport_retries": max(1, int(runtime.transport_retries)),
        "task_models": task_models,
    }


def resolve_user_gateway_runtime_file(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path).expanduser().resolve()
    override_dir = str(os.environ.get("LLMGATEWAY_USER_CONFIG_DIR", "") or "").strip()
    if override_dir:
        return (Path(override_dir).expanduser().resolve() / "config.yaml").resolve()
    explicit = str(os.environ.get("LLMGATEWAY_USER_CONFIG", "") or "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    return (Path.home() / ".llmgateway" / "config.yaml").resolve()


def load_user_gateway_runtime_profile(path: str | Path | None = None) -> dict[str, Any]:
    raw = load_gateway_user_config(resolve_user_gateway_runtime_file(path))
    if not raw:
        return {}
    try:
        return runtime_profile_from_gateway_raw(raw)
    except Exception:
        return {}


def describe_user_gateway_runtime_issue(path: str | Path | None = None) -> str | None:
    config_path = resolve_user_gateway_runtime_file(path)
    if not config_path.exists():
        return None

    try:
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"{config_path} cannot be parsed: {_compact_error(exc)}"

    if loaded is None:
        return f"{config_path} is empty."
    if not isinstance(loaded, dict):
        return f"{config_path} must contain a YAML object at the top level."

    resolved = resolve_env_refs(loaded)
    if not isinstance(resolved, dict):
        return f"{config_path} must resolve to a YAML object."

    try:
        runtime = runtime_spec_from_dict(resolved)
    except Exception as exc:
        return f"{config_path} contains an invalid llmgateway runtime: {_compact_error(exc)}"

    missing_fields: list[str] = []
    if not str(runtime.provider.base_url or "").strip():
        missing_fields.append("provider.base_url")
    if not str(runtime.provider.api_key or "").strip():
        missing_fields.append("provider.api_key")
    if not any(
        str(value or "").strip()
        for value in (runtime.strong_model, runtime.weak_model, runtime.fallback_model)
    ):
        missing_fields.append(
            "settings.strong_model / settings.weak_model / settings.fallback_model"
        )
    if missing_fields:
        return f"{config_path} is missing required field(s): {', '.join(missing_fields)}"
    return None


__all__ = [
    "describe_user_gateway_runtime_issue",
    "load_user_gateway_runtime_profile",
    "resolve_user_gateway_runtime_file",
    "runtime_profile_from_gateway_raw",
]
