"""Gateway-specific helpers for config loading."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .merge_support import (
    load_yaml_dict,
    normalize_str,
    normalize_str_dict,
    resolve_existing_file,
)


def _iter_gateway_candidate_paths(start: Path):
    for directory in [start.resolve(), *start.resolve().parents]:
        yield directory / ".llmgateway.yaml"
        yield directory / "llm-proxy" / ".llmgateway.yaml"


def discover_gateway_config(start: Path, explicit_path: str | None) -> Path | None:
    explicit = resolve_existing_file(explicit_path)
    if explicit is not None:
        return explicit
    env_candidate = resolve_existing_file(
        os.environ.get("LLMGATEWAY_CONFIG") or os.environ.get("LLMPROXY_GATEWAY_CONFIG")
    )
    if env_candidate is not None:
        return env_candidate
    for candidate in _iter_gateway_candidate_paths(start):
        if candidate.is_file():
            return candidate
    return None


def gateway_provider_sections(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    backend_llm = raw.get("backend_llm")
    providers = raw.get("providers")
    if not isinstance(backend_llm, dict) or not isinstance(providers, dict):
        return None
    provider_name = normalize_str(backend_llm.get("provider"))
    provider_cfg = providers.get(provider_name) if provider_name else {}
    return backend_llm, provider_cfg if isinstance(provider_cfg, dict) else {}


def build_gateway_backend_profile(
    backend_llm: dict[str, Any],
    provider_cfg: dict[str, Any],
) -> dict[str, Any]:
    return {
        "base_url": normalize_str(provider_cfg.get("base_url")),
        "api_key": normalize_str(provider_cfg.get("api_key")),
        "extra_headers": normalize_str_dict(provider_cfg.get("headers")),
        "provider_type": normalize_str(provider_cfg.get("provider_type")),
        "api_style": normalize_str(provider_cfg.get("api_style")),
        "model_map": normalize_str_dict(provider_cfg.get("model_map")),
        "model": normalize_str(backend_llm.get("model")),
        "task_models": normalize_str_dict(backend_llm.get("task_models")),
    }


def load_gateway_backend_profile(path: Path) -> dict[str, Any] | None:
    raw = load_yaml_dict(path)
    if not raw:
        return None
    sections = gateway_provider_sections(raw)
    if sections is None:
        return None
    backend_llm, provider_cfg = sections
    return build_gateway_backend_profile(backend_llm, provider_cfg)
