"""Generic strategy helpers for structure prompt generation.

This module keeps repository-specific assumptions out of structure_prompt.py.
It provides:
1) repository archetype detection
2) generic directory semantic descriptions
3) archetype-aware entry-file reason hints
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ARCHETYPE_MONOREPO = "monorepo"
ARCHETYPE_SERVICE = "service"
ARCHETYPE_LIBRARY = "library"
ARCHETYPE_FRONTEND = "frontend"
ARCHETYPE_INFRA = "infra"
ARCHETYPE_GENERIC = "generic"

_ARCHETYPE_VALUES = {
    ARCHETYPE_MONOREPO,
    ARCHETYPE_SERVICE,
    ARCHETYPE_LIBRARY,
    ARCHETYPE_FRONTEND,
    ARCHETYPE_INFRA,
    ARCHETYPE_GENERIC,
}


def normalize_archetype(value: str | None) -> str:
    if not value:
        return ARCHETYPE_GENERIC
    v = value.strip().lower()
    return v if v in _ARCHETYPE_VALUES else ARCHETYPE_GENERIC


def detect_repo_archetype(
    root_name: str,
    files: dict[str, dict[str, Any]],
    modules: list[dict[str, Any]],
) -> str:
    """Infer repository archetype from paths and module metadata."""
    paths = list(files.keys())
    if not paths:
        return ARCHETYPE_GENERIC

    # Monorepo heuristic: multiple meaningful top-level projects each with
    # source/build marker files.
    top_level_stats: dict[str, dict[str, int]] = {}
    for fp in paths:
        parts = Path(fp).as_posix().split("/")
        if not parts:
            continue
        top = parts[0]
        stat = top_level_stats.setdefault(top, {"files": 0, "markers": 0})
        stat["files"] += 1
        name = parts[-1].lower()
        if name in {
            "pyproject.toml",
            "package.json",
            "go.mod",
            "cargo.toml",
            "pom.xml",
            "build.gradle",
        }:
            stat["markers"] += 1
        if "src" in {p.lower() for p in parts[1:]}:
            stat["markers"] += 1

    multi_projects = sum(
        1
        for _k, v in top_level_stats.items()
        if v["files"] >= 8 and v["markers"] >= 1
    )
    if multi_projects >= 2:
        return ARCHETYPE_MONOREPO

    lower_paths = [p.lower() for p in paths]
    frontend_hits = sum(
        1
        for p in lower_paths
        if p.endswith((".tsx", ".jsx", ".vue", ".svelte", ".css", ".scss"))
        or "vite.config" in p
        or "next.config" in p
    )
    if frontend_hits >= 8:
        return ARCHETYPE_FRONTEND

    infra_hits = sum(
        1
        for p in lower_paths
        if p.endswith((".tf", ".hcl"))
        or "/k8s/" in p
        or "/helm/" in p
        or p.endswith(("docker-compose.yml", "docker-compose.yaml"))
    )
    if infra_hits >= 6:
        return ARCHETYPE_INFRA

    service_hits = sum(
        1
        for p in lower_paths
        if any(tok in p for tok in ("/server", "/gateway", "/api/", "http", "router"))
    )
    if service_hits >= 6:
        return ARCHETYPE_SERVICE

    lib_hits = sum(
        1
        for p in lower_paths
        if "/src/" in p and "/tests/" not in p and "/test/" not in p
    )
    if lib_hits >= 10:
        return ARCHETYPE_LIBRARY

    # Soft signal from module metadata when available.
    module_desc = " ".join(str(m.get("desc", "")).lower() for m in modules[:16])
    if any(k in module_desc for k in ("gateway", "proxy", "router", "server")):
        return ARCHETYPE_SERVICE
    if any(k in module_desc for k in ("indexing", "parser", "library", "sdk")):
        return ARCHETYPE_LIBRARY

    if root_name.lower() in {"infra", "infrastructure", "ops"}:
        return ARCHETYPE_INFRA
    return ARCHETYPE_GENERIC


def describe_workspace_dir(name: str, archetype: str) -> str:
    """Provide a generic semantic hint for top-level directories."""
    n = name.lower()
    archetype = normalize_archetype(archetype)

    generic = {
        "src": "Primary application/source code",
        "lib": "Reusable library source code",
        "app": "Application entry code",
        "apps": "Multiple application packages",
        "services": "Service packages",
        "packages": "Shared packages/modules",
        "modules": "Feature modules",
        "tests": "Automated tests and validation suites",
        "test": "Automated tests and validation suites",
        "docs": "Documentation and references",
        "scripts": "Developer/CI automation scripts",
        "tools": "Engineering tooling and utilities",
        "configs": "Configuration templates and profiles",
        "config": "Configuration templates and profiles",
        "infra": "Infrastructure and deployment assets",
        "deploy": "Deployment definitions",
        "gateway": "Request gateway/edge logic",
        "web": "Web frontend assets",
        "frontend": "Frontend application code",
        "backend": "Backend service code",
        "abstract_class": "Abstract interfaces and shared base classes",
        "problem_solvers": "Problem-specific solver implementations",
        "meta_coding": "Meta-programming and code-generation pipeline",
        "algebraic_solver": "Numerical/algebraic solver implementations",
        "visualization": "Visualization, plotting, and report utilities",
    }
    if n in generic:
        return generic[n]

    # Generic semantic fallbacks by token; keeps behavior portable across repos.
    if any(tok in n for tok in ("solver", "solvers", "engine")):
        return "Problem-solving and algorithm execution components"
    if any(tok in n for tok in ("meta", "codegen", "generator", "compiler", "transform")):
        return "Meta-programming and code transformation components"
    if any(tok in n for tok in ("visual", "plot", "chart", "render")):
        return "Visualization and presentation components"
    if any(tok in n for tok in ("abstract", "base", "interface")):
        return "Abstract contracts and foundational components"
    if any(tok in n for tok in ("algebra", "numeric", "linear", "math")):
        return "Numerical and mathematical computation components"
    if any(tok in n for tok in ("model", "network", "nn")):
        return "Model definitions and runtime components"
    if any(tok in n for tok in ("data", "dataset", "loader")):
        return "Data processing and loading components"

    if archetype == ARCHETYPE_MONOREPO:
        return "Workspace project/package"
    if archetype == ARCHETYPE_SERVICE:
        return "Service component"
    if archetype == ARCHETYPE_FRONTEND:
        return "Frontend component/module"
    if archetype == ARCHETYPE_INFRA:
        return "Infrastructure component"
    if archetype == ARCHETYPE_LIBRARY:
        return "Library component"
    return "Workspace module"


def entry_file_reasons_for_archetype(archetype: str) -> dict[str, str]:
    archetype = normalize_archetype(archetype)
    reasons = {
        "pyproject.toml": "Python project and dependency manifest",
        "package.json": "Node project and script manifest",
        "go.mod": "Go module manifest",
        "cargo.toml": "Rust crate manifest",
        "__main__.py": "CLI/runtime bootstrap",
        "main.py": "Main process entry",
        "main_solver.py": "Main solver orchestration entry",
        "run.py": "Runtime launcher entry",
        "start.py": "Runtime launcher entry",
        "serve.py": "Server startup entry",
        "bootstrap.py": "Bootstrap sequence entry",
        "launcher.py": "Launcher entry",
        "entrypoint.py": "Container/runtime entrypoint",
        "main.go": "Main process entry",
        "main.rs": "Main process entry",
        "cli.py": "Command-line entry",
        "server.py": "Server entry",
        "http_proxy.py": "HTTP proxy entry",
        "project_router.py": "Per-project request routing",
        "dashboard.html": "Admin dashboard UI",
    }

    if archetype in {ARCHETYPE_SERVICE, ARCHETYPE_MONOREPO}:
        reasons.update(
            {
                "api.py": "API entry/handler surface",
                "router.py": "HTTP routing surface",
                "gateway.py": "Gateway or edge orchestration",
            }
        )
    if archetype in {ARCHETYPE_FRONTEND, ARCHETYPE_MONOREPO}:
        reasons.update(
            {
                "vite.config.ts": "Frontend bundler/runtime config",
                "next.config.js": "Frontend runtime config",
                "app.tsx": "Frontend application entry",
                "main.tsx": "Frontend application entry",
            }
        )
    if archetype == ARCHETYPE_INFRA:
        reasons.update(
            {
                "main.tf": "Infrastructure root module entry",
                "terragrunt.hcl": "Infrastructure orchestration entry",
            }
        )

    return reasons
