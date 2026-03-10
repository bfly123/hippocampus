"""Render profiles for structure prompt generation."""

from __future__ import annotations

from typing import Any

_PROFILE_SMALL: dict[str, Any] = {
    "name": "small",
    "files_per_dir": 6,
    "dirs_per_dir": 8,
    "top_summary_dirs": 10,
    "tree_depth": 3,
    "module_lines": 7,
    "key_files": 12,
    "test_files": 4,
    "signature_files": 3,
    "sigs_per_file": 4,
    "llm_reading_items": 4,
    "llm_axes_items": 3,
    "llm_hotspots_items": 2,
    "include_llm_brief": False,
    "include_signatures": True,
    "prefer_l2_ratio": 0.75,
    "tree_reserve_ratio": 0.65,
}

_PROFILE_MEDIUM: dict[str, Any] = {
    "name": "medium",
    "files_per_dir": 10,
    "dirs_per_dir": 12,
    "top_summary_dirs": 18,
    "tree_depth": 4,
    "module_lines": 10,
    "key_files": 18,
    "test_files": 8,
    "signature_files": 14,
    "sigs_per_file": 10,
    "llm_reading_items": 6,
    "llm_axes_items": 5,
    "llm_hotspots_items": 4,
    "include_llm_brief": True,
    "include_signatures": True,
    "prefer_l2_ratio": 0.55,
    "tree_reserve_ratio": 0.50,
}

_PROFILE_LARGE: dict[str, Any] = {
    "name": "large",
    "files_per_dir": 14,
    "dirs_per_dir": 18,
    "top_summary_dirs": 26,
    "tree_depth": 5,
    "module_lines": 14,
    "key_files": 28,
    "test_files": 12,
    "signature_files": 24,
    "sigs_per_file": 14,
    "llm_reading_items": 8,
    "llm_axes_items": 6,
    "llm_hotspots_items": 6,
    "include_llm_brief": True,
    "include_signatures": True,
    "prefer_l2_ratio": 0.45,
    "tree_reserve_ratio": 0.40,
}

_PROFILE_XLARGE: dict[str, Any] = {
    "name": "xlarge",
    "files_per_dir": 20,
    "dirs_per_dir": 26,
    "top_summary_dirs": 36,
    "tree_depth": 6,
    "module_lines": 16,
    "key_files": 56,
    "test_files": 16,
    "signature_files": 40,
    "sigs_per_file": 18,
    "llm_reading_items": 10,
    "llm_axes_items": 8,
    "llm_hotspots_items": 8,
    "include_llm_brief": True,
    "include_signatures": True,
    "prefer_l2_ratio": 0.40,
    "tree_reserve_ratio": 0.35,
}

_RENDER_PROFILE_AUTO = "auto"
_RENDER_PROFILE_MAP = "map"
_RENDER_PROFILE_DEEP = "deep"
_RENDER_PROFILE_VALUES = {
    _RENDER_PROFILE_AUTO,
    _RENDER_PROFILE_MAP,
    _RENDER_PROFILE_DEEP,
}


def normalize_render_profile(render_profile: str | None) -> str:
    if render_profile is None:
        return _RENDER_PROFILE_AUTO
    value = render_profile.strip().lower()
    if not value:
        return _RENDER_PROFILE_AUTO
    return value if value in _RENDER_PROFILE_VALUES else _RENDER_PROFILE_AUTO


def profile_for_budget(
    max_tokens: int, render_profile: str = _RENDER_PROFILE_AUTO
) -> dict[str, Any]:
    if max_tokens <= 2500:
        base = dict(_PROFILE_SMALL)
    elif max_tokens <= 6000:
        base = dict(_PROFILE_MEDIUM)
    elif max_tokens <= 9000:
        base = dict(_PROFILE_LARGE)
    else:
        base = dict(_PROFILE_XLARGE)

    mode = normalize_render_profile(render_profile)
    if mode == _RENDER_PROFILE_MAP:
        base["name"] = f"{base['name']}-map"
        base["tree_depth"] = min(int(base["tree_depth"]), 4)
        base["files_per_dir"] = min(int(base["files_per_dir"]), 10)
        base["dirs_per_dir"] = min(int(base["dirs_per_dir"]), 14)
        base["module_lines"] = min(int(base["module_lines"]), 10)
        base["key_files"] = max(14, min(int(base["key_files"]), 22))
        base["test_files"] = min(int(base["test_files"]), 6)
        base["signature_files"] = max(8, min(int(base["signature_files"]), 16))
        base["sigs_per_file"] = max(6, min(int(base["sigs_per_file"]), 10))
        base["llm_reading_items"] = min(int(base["llm_reading_items"]), 6)
        base["llm_axes_items"] = min(int(base["llm_axes_items"]), 5)
        base["llm_hotspots_items"] = min(int(base["llm_hotspots_items"]), 4)
        base["prefer_l2_ratio"] = 0.62
        base["tree_reserve_ratio"] = 0.52
        base["include_llm_brief"] = max_tokens >= 3000
        base["include_signatures"] = True
    elif mode == _RENDER_PROFILE_DEEP:
        base["name"] = f"{base['name']}-deep"
        base["tree_depth"] = max(int(base["tree_depth"]), 5)
        base["files_per_dir"] = max(int(base["files_per_dir"]), 14)
        base["dirs_per_dir"] = max(int(base["dirs_per_dir"]), 18)
        base["module_lines"] = max(int(base["module_lines"]), 16)
        base["key_files"] = max(int(base["key_files"]), 40)
        base["test_files"] = max(int(base["test_files"]), 12)
        base["signature_files"] = max(int(base["signature_files"]), 34)
        base["sigs_per_file"] = max(int(base["sigs_per_file"]), 16)
        base["llm_reading_items"] = max(int(base["llm_reading_items"]), 10)
        base["llm_axes_items"] = max(int(base["llm_axes_items"]), 8)
        base["llm_hotspots_items"] = max(int(base["llm_hotspots_items"]), 8)
        base["prefer_l2_ratio"] = 0.36
        base["tree_reserve_ratio"] = 0.30
        base["include_llm_brief"] = True
        base["include_signatures"] = True

    return base
