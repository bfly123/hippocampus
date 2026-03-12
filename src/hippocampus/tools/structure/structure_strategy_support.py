"""Support data and predicates for structure strategy helpers."""

from __future__ import annotations

ARCHETYPE_MONOREPO = "monorepo"
ARCHETYPE_SERVICE = "service"
ARCHETYPE_LIBRARY = "library"
ARCHETYPE_FRONTEND = "frontend"
ARCHETYPE_INFRA = "infra"
ARCHETYPE_GENERIC = "generic"

ARCHETYPE_VALUES = {
    ARCHETYPE_MONOREPO,
    ARCHETYPE_SERVICE,
    ARCHETYPE_LIBRARY,
    ARCHETYPE_FRONTEND,
    ARCHETYPE_INFRA,
    ARCHETYPE_GENERIC,
}

GENERIC_DIR_DESCRIPTIONS = {
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

TOKEN_DIR_DESCRIPTIONS = (
    (
        ("solver", "solvers", "engine"),
        "Problem-solving and algorithm execution components",
    ),
    (
        ("meta", "codegen", "generator", "compiler", "transform"),
        "Meta-programming and code transformation components",
    ),
    (
        ("visual", "plot", "chart", "render"),
        "Visualization and presentation components",
    ),
    (
        ("abstract", "base", "interface"),
        "Abstract contracts and foundational components",
    ),
    (
        ("algebra", "numeric", "linear", "math"),
        "Numerical and mathematical computation components",
    ),
    (("model", "network", "nn"), "Model definitions and runtime components"),
    (("data", "dataset", "loader"), "Data processing and loading components"),
)

ARCHETYPE_FALLBACK_DESCRIPTIONS = {
    ARCHETYPE_MONOREPO: "Workspace project/package",
    ARCHETYPE_SERVICE: "Service component",
    ARCHETYPE_FRONTEND: "Frontend component/module",
    ARCHETYPE_INFRA: "Infrastructure component",
    ARCHETYPE_LIBRARY: "Library component",
}

BASE_ENTRY_FILE_REASONS = {
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

SERVICE_ENTRY_FILE_REASONS = {
    "api.py": "API entry/handler surface",
    "router.py": "HTTP routing surface",
    "gateway.py": "Gateway or edge orchestration",
}

FRONTEND_ENTRY_FILE_REASONS = {
    "vite.config.ts": "Frontend bundler/runtime config",
    "next.config.js": "Frontend runtime config",
    "app.tsx": "Frontend application entry",
    "main.tsx": "Frontend application entry",
}

INFRA_ENTRY_FILE_REASONS = {
    "main.tf": "Infrastructure root module entry",
    "terragrunt.hcl": "Infrastructure orchestration entry",
}

PATH_ARCHETYPE_RULES = (
    (ARCHETYPE_FRONTEND, 8, "_is_frontend_path"),
    (ARCHETYPE_INFRA, 6, "_is_infra_path"),
    (ARCHETYPE_SERVICE, 6, "_is_service_path"),
    (ARCHETYPE_LIBRARY, 10, "_is_library_path"),
)


def is_frontend_path(path: str) -> bool:
    return (
        path.endswith((".tsx", ".jsx", ".vue", ".svelte", ".css", ".scss"))
        or "vite.config" in path
        or "next.config" in path
    )


def is_infra_path(path: str) -> bool:
    return (
        path.endswith((".tf", ".hcl"))
        or "/k8s/" in path
        or "/helm/" in path
        or path.endswith(("docker-compose.yml", "docker-compose.yaml"))
    )


def is_service_path(path: str) -> bool:
    return any(token in path for token in ("/server", "/gateway", "/api/", "http", "router"))


def is_library_path(path: str) -> bool:
    return "/src/" in path and "/tests/" not in path and "/test/" not in path
