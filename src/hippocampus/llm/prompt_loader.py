from __future__ import annotations

from .prompt_paths import packaged_prompt_exists, packaged_prompt_text, resolve_prompt_file


def load_prompt_text(name: str, *, project_root=None) -> str:
    path = resolve_prompt_file(name, project_root=project_root)
    if path is not None:
        return path.read_text(encoding="utf-8").strip()
    if packaged_prompt_exists(name):
        return packaged_prompt_text(name)
    raise FileNotFoundError(f"Prompt not found: {name}")


def resolve_prompt_text(value: object, *, project_root=None) -> str:
    text = str(value or "").strip()
    if not text.startswith("prompt:"):
        return text
    name = text[len("prompt:"):].strip()
    if not name:
        return ""
    return load_prompt_text(name, project_root=project_root)


def render_prompt(name: str, *, project_root=None, **kwargs) -> str:
    template = load_prompt_text(name, project_root=project_root)
    return template.format(**kwargs)


__all__ = ["load_prompt_text", "render_prompt", "resolve_prompt_text"]
