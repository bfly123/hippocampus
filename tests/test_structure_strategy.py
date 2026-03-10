"""Tests for generic structure strategy helpers."""

from __future__ import annotations

from hippocampus.tools.structure_strategy import (
    ARCHETYPE_FRONTEND,
    ARCHETYPE_GENERIC,
    ARCHETYPE_MONOREPO,
    ARCHETYPE_SERVICE,
    detect_repo_archetype,
    describe_workspace_dir,
    entry_file_reasons_for_archetype,
    normalize_archetype,
)


def test_normalize_archetype_unknown_to_generic() -> None:
    assert normalize_archetype("unknown-kind") == ARCHETYPE_GENERIC


def test_detect_repo_archetype_monorepo() -> None:
    files = {
        "proj_a/pyproject.toml": {},
        "proj_a/src/a/main.py": {},
        "proj_a/src/a/util.py": {},
        "proj_a/src/a/x.py": {},
        "proj_a/src/a/y.py": {},
        "proj_a/src/a/z.py": {},
        "proj_a/tests/test_a.py": {},
        "proj_a/README.md": {},
        "proj_b/package.json": {},
        "proj_b/src/b/index.ts": {},
        "proj_b/src/b/app.ts": {},
        "proj_b/src/b/router.ts": {},
        "proj_b/src/b/config.ts": {},
        "proj_b/src/b/view.ts": {},
        "proj_b/src/b/hooks.ts": {},
        "proj_b/tests/test_b.ts": {},
    }
    archetype = detect_repo_archetype(root_name="repo", files=files, modules=[])
    assert archetype == ARCHETYPE_MONOREPO


def test_detect_repo_archetype_frontend() -> None:
    files = {
        "src/main.tsx": {},
        "src/app.tsx": {},
        "src/pages/home.tsx": {},
        "src/pages/about.tsx": {},
        "src/components/a.tsx": {},
        "src/components/b.tsx": {},
        "src/components/c.tsx": {},
        "src/styles/app.css": {},
        "vite.config.ts": {},
    }
    archetype = detect_repo_archetype(root_name="ui", files=files, modules=[])
    assert archetype == ARCHETYPE_FRONTEND


def test_detect_repo_archetype_service_from_paths() -> None:
    files = {
        "src/server.py": {},
        "src/api/router.py": {},
        "src/api/handlers.py": {},
        "src/gateway.py": {},
        "src/http_proxy.py": {},
        "src/service/http_client.py": {},
        "src/service/router_map.py": {},
        "src/service/api_server.py": {},
    }
    archetype = detect_repo_archetype(root_name="svc", files=files, modules=[])
    assert archetype == ARCHETYPE_SERVICE


def test_describe_workspace_dir_generic() -> None:
    assert "source" in describe_workspace_dir("src", ARCHETYPE_GENERIC).lower()
    assert "tests" in describe_workspace_dir("tests", ARCHETYPE_GENERIC).lower()


def test_entry_file_reasons_archetype_extends_base() -> None:
    service = entry_file_reasons_for_archetype(ARCHETYPE_SERVICE)
    assert "pyproject.toml" in service
    assert "router.py" in service

