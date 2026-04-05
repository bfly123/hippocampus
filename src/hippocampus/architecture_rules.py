from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


RULES_FILE_NAME = ".architecture-rules.toml"


@dataclass(frozen=True)
class ArchitectureRules:
    ignore_paths: tuple[str, ...] = ()
    ignore_globs: tuple[str, ...] = ()
    ignore_extensions: tuple[str, ...] = ()
    cleanup_extra_kinds: tuple[str, ...] = ("doc", "config", "prompt", "script")


def _normalize_relpath(value: str | Path) -> str:
    text = str(value or "").strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text.rstrip("/")


def _string_list(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    values: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text = _normalize_relpath(str(item or "").strip())
        if not text or text in seen:
            continue
        seen.add(text)
        values.append(text)
    return tuple(values)


def _extension_list(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    values: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text = str(item or "").strip().lower()
        if not text:
            continue
        if not text.startswith("."):
            text = f".{text}"
        if text in seen:
            continue
        seen.add(text)
        values.append(text)
    return tuple(values)


def _section_rules(raw: object, *, default_cleanup_extra_kinds: tuple[str, ...] = ()) -> ArchitectureRules:
    if not isinstance(raw, dict):
        return ArchitectureRules(cleanup_extra_kinds=default_cleanup_extra_kinds)
    return ArchitectureRules(
        ignore_paths=_string_list(raw.get("ignore_paths", [])),
        ignore_globs=_string_list(raw.get("ignore_globs", [])),
        ignore_extensions=_extension_list(raw.get("ignore_extensions", [])),
        cleanup_extra_kinds=_string_list(raw.get("cleanup_extra_kinds", list(default_cleanup_extra_kinds))),
    )


def _merge_lists(shared: tuple[str, ...], specific: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in (*shared, *specific):
        if item in seen:
            continue
        seen.add(item)
        merged.append(item)
    return tuple(merged)


def _merge_rules(shared: ArchitectureRules, specific: ArchitectureRules) -> ArchitectureRules:
    return ArchitectureRules(
        ignore_paths=_merge_lists(shared.ignore_paths, specific.ignore_paths),
        ignore_globs=_merge_lists(shared.ignore_globs, specific.ignore_globs),
        ignore_extensions=_merge_lists(shared.ignore_extensions, specific.ignore_extensions),
        cleanup_extra_kinds=_merge_lists(shared.cleanup_extra_kinds, specific.cleanup_extra_kinds),
    )


def load_architecture_rules(project_root: str | Path, *, tool_name: str) -> ArchitectureRules:
    root = Path(project_root).resolve()
    path = root / RULES_FILE_NAME
    if not path.exists():
        default_cleanup = ("doc", "config", "prompt", "script") if tool_name == "archi" else ()
        return ArchitectureRules(cleanup_extra_kinds=default_cleanup)
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        default_cleanup = ("doc", "config", "prompt", "script") if tool_name == "archi" else ()
        return ArchitectureRules(cleanup_extra_kinds=default_cleanup)
    if not isinstance(raw, dict):
        default_cleanup = ("doc", "config", "prompt", "script") if tool_name == "archi" else ()
        return ArchitectureRules(cleanup_extra_kinds=default_cleanup)
    shared = _section_rules(raw.get("shared", {}))
    specific = _section_rules(
        raw.get(tool_name, {}),
        default_cleanup_extra_kinds=("doc", "config", "prompt", "script") if tool_name == "archi" else (),
    )
    return _merge_rules(shared, specific)


def load_hippo_rules(project_root: str | Path) -> ArchitectureRules:
    return load_architecture_rules(project_root, tool_name="hippo")


def path_is_ignored(path: str | Path, rules: ArchitectureRules | None) -> bool:
    if rules is None:
        return False
    normalized = _normalize_relpath(path)
    if not normalized:
        return False
    suffix = Path(normalized).suffix.lower()
    if suffix and suffix in set(rules.ignore_extensions):
        return True
    for candidate in rules.ignore_paths:
        if normalized == candidate or normalized.startswith(f"{candidate}/"):
            return True
    posix_path = PurePosixPath(normalized)
    for pattern in rules.ignore_globs:
        if fnmatchcase(normalized, pattern) or posix_path.match(pattern):
            return True
    return False


__all__ = [
    "ArchitectureRules",
    "RULES_FILE_NAME",
    "load_architecture_rules",
    "load_hippo_rules",
    "path_is_ignored",
]
