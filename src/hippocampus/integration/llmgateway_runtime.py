from __future__ import annotations

from pathlib import Path
from typing import Any

from llmgateway.config import (
    load_user_config as load_gateway_user_config,
    resolve_user_config_file as resolve_gateway_user_config_file,
    runtime_spec_from_dict,
)


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


def load_user_gateway_runtime_profile(path: str | Path | None = None) -> dict[str, Any]:
    raw = load_gateway_user_config(path)
    if not raw:
        return {}
    try:
        return runtime_profile_from_gateway_raw(raw)
    except Exception:
        return {}


def resolve_user_gateway_runtime_file(path: str | Path | None = None) -> Path:
    return resolve_gateway_user_config_file(path)


__all__ = [
    "load_user_gateway_runtime_profile",
    "resolve_user_gateway_runtime_file",
    "runtime_profile_from_gateway_raw",
]
