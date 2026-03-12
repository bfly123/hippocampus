"""Shared fixtures and helpers for incremental cache tests."""

from __future__ import annotations

import json

import pytest

from hippocampus.tools.index_gen import (
    _content_hash,
    _phase2_input_hash,
    _phase3_module_input_hash,
    _load_phase2_cache,
    _load_phase3_cache,
    _save_phase2_cache,
    _save_phase3_cache,
)


@pytest.fixture
def phase1_results():
    return {
        "src/main.py": {"desc": "Entry point", "tags": ["cli", "python"]},
        "src/utils.py": {"desc": "Utility helpers", "tags": ["utils", "python"]},
        "src/config.py": {"desc": "Config loader", "tags": ["config", "python"]},
        "src/server.py": {"desc": "HTTP server", "tags": ["http", "python"]},
    }


@pytest.fixture
def modules_list():
    return [
        {"id": "mod:core", "desc": "Core logic"},
        {"id": "mod:infra", "desc": "Infrastructure"},
    ]


@pytest.fixture
def file_to_module():
    return {
        "src/main.py": "mod:core",
        "src/utils.py": "mod:core",
        "src/config.py": "mod:infra",
        "src/server.py": "mod:infra",
    }


def make_mock_config():
    from hippocampus.config import HippoConfig

    return HippoConfig()


def mock_llm_2a_response():
    return json.dumps(
        {
            "modules": [
                {"id": "mod:core", "desc": "Core logic"},
                {"id": "mod:infra", "desc": "Infrastructure"},
            ]
        }
    )


def mock_llm_2b_response(files):
    assignments = []
    for file_path in files:
        module_id = "mod:core" if "main" in file_path or "utils" in file_path else "mod:infra"
        assignments.append({"file": file_path, "module_id": module_id})
    return json.dumps(assignments)


__all__ = [
    "_content_hash",
    "_load_phase2_cache",
    "_load_phase3_cache",
    "_phase2_input_hash",
    "_phase3_module_input_hash",
    "_save_phase2_cache",
    "_save_phase3_cache",
    "file_to_module",
    "make_mock_config",
    "mock_llm_2a_response",
    "mock_llm_2b_response",
    "modules_list",
    "phase1_results",
]
