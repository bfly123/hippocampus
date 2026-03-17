from __future__ import annotations

import os
from pathlib import Path


HIPPOCAMPUS_LLM_CONFIG_NAME = "config.yaml"


def user_config_dir() -> Path:
    override = str(os.environ.get("HIPPOCAMPUS_USER_CONFIG_DIR", "") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".hippocampus").resolve()


def project_state_dir(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / ".hippocampus"


def resolve_hippo_llm_config_file(project_root: str | Path | None = None) -> Path:
    if project_root is not None:
        local_override = project_state_dir(project_root) / HIPPOCAMPUS_LLM_CONFIG_NAME
        if local_override.exists():
            return local_override
    return user_config_dir() / HIPPOCAMPUS_LLM_CONFIG_NAME


__all__ = [
    "HIPPOCAMPUS_LLM_CONFIG_NAME",
    "project_state_dir",
    "resolve_hippo_llm_config_file",
    "user_config_dir",
]
