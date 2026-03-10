from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path


def packaged_prompt_resource(name: str):
    return files("hippocampus").joinpath("resources", "prompts", name)


def project_prompts_dir(project_root: str | Path | None) -> Path | None:
    if project_root is None:
        return None
    return Path(project_root).resolve() / ".hippocampus" / "prompts"


def legacy_project_prompts_dir(project_root: str | Path | None) -> Path | None:
    if project_root is None:
        return None
    return Path(project_root).resolve() / "hippocampus" / "prompts"


def override_prompts_dir() -> Path | None:
    override = str(os.environ.get("HIPPOCAMPUS_PROMPTS_DIR", "") or "").strip()
    if not override:
        return None
    return Path(override).expanduser().resolve()


def resolve_prompt_file(name: str, project_root: str | Path | None = None) -> Path | None:
    override = override_prompts_dir()
    if override is not None:
        candidate = override / name
        if candidate.exists():
            return candidate

    project_dir = project_prompts_dir(project_root)
    if project_dir is not None:
        candidate = project_dir / name
        if candidate.exists():
            return candidate

    legacy_dir = legacy_project_prompts_dir(project_root)
    if legacy_dir is not None:
        candidate = legacy_dir / name
        if candidate.exists():
            return candidate

    return None


def packaged_prompt_exists(name: str) -> bool:
    try:
        return packaged_prompt_resource(name).is_file()
    except Exception:
        return False


def packaged_prompt_text(name: str) -> str:
    return packaged_prompt_resource(name).read_text(encoding="utf-8").strip()


__all__ = [
    "legacy_project_prompts_dir",
    "override_prompts_dir",
    "packaged_prompt_exists",
    "packaged_prompt_resource",
    "packaged_prompt_text",
    "project_prompts_dir",
    "resolve_prompt_file",
]
