"""Merge and normalization helpers for config loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def normalize_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def normalize_str_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for key, raw_value in value.items():
        norm_key = normalize_str(key)
        norm_value = normalize_str(raw_value)
        if norm_key and norm_value:
            out[norm_key] = norm_value
    return out


def load_yaml_dict(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dicts(merged[key], value)
            continue
        merged[key] = value
    return merged


def is_empty_config_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (dict, list, tuple, set)):
        return not value
    return False


def merge_dicts_skipping_empty_defaults(
    base: dict[str, Any],
    override: dict[str, Any],
    *,
    defaults: dict[str, Any],
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        default_value = defaults.get(key)
        current_value = merged.get(key)
        if isinstance(value, dict) and isinstance(current_value, dict):
            child_defaults = default_value if isinstance(default_value, dict) else {}
            merged[key] = merge_dicts_skipping_empty_defaults(
                current_value,
                value,
                defaults=child_defaults,
            )
            continue
        if is_empty_config_value(value):
            continue
        if default_value is not None and value == default_value:
            continue
        merged[key] = value
    return merged


def infer_project_root(config_path: Path | None, project_root: Path | None) -> Path | None:
    if project_root is not None:
        return project_root.resolve()
    if config_path is None:
        return None
    resolved = config_path.resolve()
    if resolved.name == "config.yaml" and resolved.parent.name == ".hippocampus":
        return resolved.parent.parent
    return resolved.parent


def resolve_existing_file(raw_path: str | None) -> Path | None:
    normalized = normalize_str(raw_path)
    if not normalized:
        return None
    candidate = Path(normalized).expanduser().resolve()
    return candidate if candidate.is_file() else None
