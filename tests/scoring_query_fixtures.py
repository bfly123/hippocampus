"""Shared fixtures for scoring and query tests."""

from __future__ import annotations

import pytest

from hippocampus.scoring import compute_module_scores


@pytest.fixture
def sample_index():
    return {
        "version": 2,
        "schema": "hippocampus-index/v2",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "project": {
            "overview": "A sample project for testing.",
            "architecture": "Monolithic Python app.",
            "scale": {"files": 6, "modules": 3, "primary_lang": "python"},
        },
        "modules": [
            {"id": "mod-core", "desc": "Core engine", "file_count": 3},
            {"id": "mod-api", "desc": "API layer", "file_count": 2},
            {"id": "mod-test", "desc": "Test suite", "file_count": 1},
        ],
        "files": {
            "src/main.py": {
                "id": "file:src/main.py",
                "type": "file",
                "name": "main.py",
                "lang": "python",
                "desc": "Application entrypoint",
                "tags": ["entrypoint", "python"],
                "module": "mod-core",
                "signatures": [
                    {"name": "main", "kind": "function", "line": 1, "desc": "Entry"},
                    {"name": "setup", "kind": "function", "line": 10, "desc": "Init"},
                ],
            },
            "src/engine.py": {
                "id": "file:src/engine.py",
                "type": "file",
                "name": "engine.py",
                "lang": "python",
                "desc": "Core processing engine",
                "tags": ["core", "python"],
                "module": "mod-core",
                "signatures": [
                    {"name": "Engine", "kind": "class", "line": 1, "desc": "Main engine"},
                    {
                        "name": "process",
                        "kind": "method",
                        "line": 5,
                        "parent": "Engine",
                        "desc": "Process data",
                    },
                    {
                        "name": "validate",
                        "kind": "method",
                        "line": 20,
                        "parent": "Engine",
                        "desc": "Validate input",
                    },
                ],
            },
            "src/utils.py": {
                "id": "file:src/utils.py",
                "type": "file",
                "name": "utils.py",
                "lang": "python",
                "desc": "Utility helpers",
                "tags": ["util", "python"],
                "module": "mod-core",
                "signatures": [
                    {"name": "helper", "kind": "function", "line": 1, "desc": "A helper"}
                ],
            },
            "src/api/routes.py": {
                "id": "file:src/api/routes.py",
                "type": "file",
                "name": "routes.py",
                "lang": "python",
                "desc": "HTTP route definitions",
                "tags": ["api", "python"],
                "module": "mod-api",
                "signatures": [
                    {"name": "get_users", "kind": "function", "line": 1, "desc": "List users"},
                    {
                        "name": "create_user",
                        "kind": "function",
                        "line": 10,
                        "desc": "Create user",
                    },
                ],
            },
            "src/api/middleware.py": {
                "id": "file:src/api/middleware.py",
                "type": "file",
                "name": "middleware.py",
                "lang": "python",
                "desc": "Request middleware",
                "tags": ["api", "python"],
                "module": "mod-api",
                "signatures": [],
            },
            "tests/test_engine.py": {
                "id": "file:tests/test_engine.py",
                "type": "file",
                "name": "test_engine.py",
                "lang": "python",
                "desc": "Engine unit tests",
                "tags": ["test", "python"],
                "module": "mod-test",
                "signatures": [
                    {
                        "name": "test_process",
                        "kind": "function",
                        "line": 1,
                        "desc": "Test process",
                    }
                ],
            },
        },
        "stats": {"total_files": 6, "total_modules": 3, "total_signatures": 9},
    }


@pytest.fixture
def scored_index(sample_index):
    compute_module_scores(sample_index)
    return sample_index


__all__ = ["sample_index", "scored_index"]
