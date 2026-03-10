"""Role classification helpers for structure prompt."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..utils import is_doc

ROLE_SOURCE = "source"
ROLE_TEST = "test"
ROLE_CONFIG = "config"
ROLE_DOCS = "docs"

_TEST_DIRS = {"tests", "test", "__tests__"}
_TEST_SUFFIXES = {"_test.py", "_spec.py"}
_TEST_PREFIXES = {"test_", "conftest."}
_CONFIG_NAMES = {
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "makefile",
    "dockerfile",
    ".env",
    "tox.ini",
    "noxfile.py",
}
_CONFIG_EXTS = {".yml", ".yaml", ".toml", ".cfg", ".ini"}
_KEY_FILE_BONUS = {
    "main.py": 8,
    "__main__.py": 8,
    "cli.py": 7,
    "server.py": 7,
    "http_proxy.py": 8,
    "project_router.py": 8,
    "config.py": 6,
    "dashboard.html": 6,
}
_ENTRY_SUFFIX_REASONS = {
    "_main.py": "Module runtime entry",
    "_entry.py": "Module entry wrapper",
    "_cli.py": "Command-line entry",
    "_server.py": "Service server entry",
    "_gateway.py": "Gateway entry",
    "_router.py": "Routing entry",
    "_solver.py": "Solver orchestration entry",
}
_ENTRY_STEM_REASONS = {
    "main_solver": "Main solver orchestration entry",
    "entrypoint": "Container/runtime entrypoint",
    "bootstrap": "Bootstrap sequence entry",
    "launcher": "Runtime launcher entry",
    "serve": "Server startup entry",
    "start": "Runtime startup entry",
    "run": "Runtime launcher entry",
}


def classify_file_role(file_path: str, file_data: dict[str, Any]) -> str:
    p = Path(file_path)
    parts_lower = [part.lower() for part in p.parts]
    name_lower = p.name.lower()

    if any(d in parts_lower for d in _TEST_DIRS):
        return ROLE_TEST
    if any(name_lower.startswith(pf) for pf in _TEST_PREFIXES):
        return ROLE_TEST
    if any(name_lower.endswith(sf) for sf in _TEST_SUFFIXES):
        return ROLE_TEST

    if name_lower in _CONFIG_NAMES or p.suffix.lower() in _CONFIG_EXTS:
        return ROLE_CONFIG

    if is_doc(p):
        return ROLE_DOCS

    tags = {t.lower() for t in file_data.get("tags", [])}
    if tags & {"test", "spec", "mock"}:
        return ROLE_TEST
    if tags & {"config", "ci", "setup"}:
        return ROLE_CONFIG
    if tags & {"docs", "asset"}:
        return ROLE_DOCS

    return ROLE_SOURCE
