from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_user_llm_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def build_user_llm_config(
    *,
    base_url: str,
    api_key: str,
    model: str,
    provider_type: str = "glm",
    api_style: str = "openai_responses",
    max_concurrent: int = 4,
    retry_max: int = 3,
    timeout: int = 120,
) -> dict[str, Any]:
    model = str(model).strip()
    return {
        "llm": {
            "provider_type": str(provider_type).strip(),
            "api_style": str(api_style).strip(),
            "base_url": str(base_url).strip(),
            "api_base": str(base_url).strip(),
            "api_key": str(api_key).strip(),
            "fallback_model": model,
            "phase_models": {
                "phase_1": model,
                "phase_2a": model,
                "phase_2b": model,
                "phase_3a": model,
                "phase_3b": model,
                "architect": model,
            },
            "max_concurrent": max(1, int(max_concurrent)),
            "retry_max": max(1, int(retry_max)),
            "timeout": max(1, int(timeout)),
        }
    }


def write_user_llm_config(
    path: Path,
    *,
    base_url: str,
    api_key: str,
    model: str,
    provider_type: str = "glm",
    api_style: str = "openai_responses",
    max_concurrent: int = 4,
    retry_max: int = 3,
    timeout: int = 120,
) -> None:
    payload = build_user_llm_config(
        base_url=base_url,
        api_key=api_key,
        model=model,
        provider_type=provider_type,
        api_style=api_style,
        max_concurrent=max_concurrent,
        retry_max=retry_max,
        timeout=timeout,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


__all__ = ["build_user_llm_config", "load_user_llm_config", "write_user_llm_config"]
