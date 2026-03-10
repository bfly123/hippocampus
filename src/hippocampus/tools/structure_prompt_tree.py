"""Tree rendering helpers for structure prompt."""

from __future__ import annotations

from typing import Any, Iterable

from ..types import TreeNode

_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        "build",
        "dist",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        ".venv",
        "venv",
        "env",
        ".aider.tags.cache.v4",
        ".llmproxy",
        ".ccb",
        ".hippocampus",
        "vendor",
        "tmp",
        "tmp_hippo_llm_smoke",
        "fangan",
        "plans",
        "claude_skills",
    }
)
_SKIP_DIR_SUFFIXES = frozenset({".egg-info"})
_SKIP_PATH_PARTS = frozenset({"history", "snapshots"})
_KEEP_HIDDEN_DIRS = frozenset({".github", ".devcontainer"})
_SKIP_FILE_SUFFIXES = frozenset({".log", ".pid", ".tmp", ".cache", ".val", ".pyc", ".pyo"})
_SKIP_FILE_NAMES = frozenset({".ds_store", "thumbs.db"})


def normalized_parts(parts: Iterable[str]) -> tuple[str, ...]:
    return tuple(part for part in parts if part and part != ".")


def split_path(path: str) -> tuple[str, ...]:
    return normalized_parts(str(path or "").replace("\\", "/").split("/"))


def is_noise_path_parts(parts: tuple[str, ...]) -> bool:
    lower_parts = [p.lower() for p in parts]
    return any(p in _SKIP_PATH_PARTS for p in lower_parts)


def is_noise_file_path(file_path: str) -> bool:
    parts = split_path(file_path)
    if not parts:
        return False
    lower_parts = [p.lower() for p in parts]
    if any(p in _SKIP_DIR_NAMES for p in lower_parts):
        return True
    if any(p in _SKIP_PATH_PARTS for p in lower_parts):
        return True
    name = parts[-1].lower()
    if name in _SKIP_FILE_NAMES:
        return True
    if any(name.endswith(sfx) for sfx in _SKIP_FILE_SUFFIXES):
        return True
    return False


def skip_dir(name: str, parent_parts: tuple[str, ...] = ()) -> bool:
    if name == ".":
        return False
    lower = name.lower()
    if lower in _SKIP_DIR_NAMES:
        return True
    if any(lower.endswith(sfx) for sfx in _SKIP_DIR_SUFFIXES):
        return True
    if lower.startswith(".") and lower not in _KEEP_HIDDEN_DIRS:
        return True
    full = normalized_parts(parent_parts + (name,))
    return is_noise_path_parts(full)


def skip_file(name: str, parent_parts: tuple[str, ...]) -> bool:
    lower = name.lower()
    if lower in _SKIP_FILE_NAMES:
        return True
    if any(lower.endswith(sfx) for sfx in _SKIP_FILE_SUFFIXES):
        return True
    if lower.startswith(".") and lower not in {".gitignore", ".env.example"}:
        return True
    full = normalized_parts(parent_parts + (name,))
    return is_noise_path_parts(full)


def render_node(
    node: TreeNode,
    depth: int = 0,
    parent_parts: tuple[str, ...] = (),
    profile: dict[str, Any] | None = None,
) -> str:
    profile = profile or {}
    files_per_dir = int(profile.get("files_per_dir", 10))
    dirs_per_dir = int(profile.get("dirs_per_dir", 12))
    tree_depth = int(profile.get("tree_depth", 4))

    prefix = "  " * depth
    if node.type == "file":
        return f"{prefix}{node.name}\n"

    if skip_dir(node.name, parent_parts):
        return ""

    current_parts = normalized_parts(parent_parts + (() if node.name == "." else (node.name,)))
    files = [c for c in node.children if c.type == "file" and not skip_file(c.name, current_parts)]
    dirs = [c for c in node.children if c.type == "dir" and not skip_dir(c.name, current_parts)]
    files.sort(key=lambda c: c.name.lower())
    dirs.sort(key=lambda c: c.name.lower())

    out: list[str] = [f"{prefix}{node.name}/\n"]
    if depth >= tree_depth:
        out.append(f"{prefix}  ... ({len(files)} files, {len(dirs)} dirs)\n")
        return "".join(out)

    for f in files[:files_per_dir]:
        out.append(f"{prefix}  {f.name}\n")
    if len(files) > files_per_dir:
        out.append(f"{prefix}  ... (+{len(files) - files_per_dir} more files)\n")

    for d in dirs[:dirs_per_dir]:
        out.append(render_node(d, depth + 1, current_parts, profile))
    if len(dirs) > dirs_per_dir:
        out.append(f"{prefix}  ... (+{len(dirs) - dirs_per_dir} more dirs)\n")
    return "".join(out)


def truncate_tree(
    node: TreeNode,
    max_chars: int,
    profile: dict[str, Any] | None = None,
) -> str:
    profile = profile or {}
    files_per_dir = int(profile.get("files_per_dir", 10))
    top_summary_dirs = int(profile.get("top_summary_dirs", 18))

    full = render_node(node, profile=profile)
    if len(full) <= max_chars:
        return full

    lines = ["./"]
    dirs = [c for c in node.children if c.type == "dir" and not skip_dir(c.name, ())]
    files = [c for c in node.children if c.type == "file" and not skip_file(c.name, ())]

    for f in sorted(files, key=lambda c: c.name.lower())[:files_per_dir]:
        lines.append(f"  {f.name}")

    sorted_dirs = sorted(dirs, key=lambda c: c.name.lower())
    for child in sorted_dirs[:top_summary_dirs]:
        child_dirs = [c for c in child.children if c.type == "dir" and not skip_dir(c.name, (child.name,))]
        child_files = [c for c in child.children if c.type == "file" and not skip_file(c.name, (child.name,))]
        lines.append(f"  {child.name}/ ({len(child_files)} files, {len(child_dirs)} dirs)")

    if len(sorted_dirs) > top_summary_dirs:
        lines.append(f"  ... (+{len(sorted_dirs) - top_summary_dirs} more top-level dirs)")

    return "\n".join(lines) + "\n"
