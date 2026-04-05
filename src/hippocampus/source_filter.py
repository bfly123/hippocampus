"""Project file classification for architecture-oriented indexing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .architecture_rules import ArchitectureRules, load_hippo_rules, path_is_ignored
from .constants import FILE_MANIFEST_FILE
from .parsers.lang_map import probe_file_language
from .utils import is_doc, is_hidden, is_runtime_artifact, write_json

_ARCHITECTURE_EXCLUDED_DIRS = frozenset(
    {
        "vendor",
        "vendors",
        "third_party",
        "third-party",
        "node_modules",
        "dist",
        "build",
        "target",
        "out",
        "bin",
        "obj",
        "coverage",
        "htmlcov",
        ".next",
        ".nuxt",
        ".svelte-kit",
        ".parcel-cache",
        ".cache",
        "tmp",
        "temp",
        ".tmp",
        "release-flow-test",
        "local-test-env",
        ".tox",
        ".eggs",
        ".gradle",
        ".dart_tool",
        ".terraform",
        "__pycache__",
        "site-packages",
    }
)
_INFRA_DIR_MARKERS = frozenset({"infra", "terraform", "helm", "charts", "k8s", "deploy", "deployment"})
_FIXTURE_DIR_MARKERS = frozenset({"fixtures", "fixture", "mocks", "mock", "testdata", "samples", "sample_data"})
_TEST_SEGMENTS = frozenset(
    {
        "test",
        "tests",
        "__tests__",
        "spec",
        "specs",
        "unittest",
        "unittests",
        "integrationtest",
        "integrationtests",
        "e2e",
        "e2etests",
        "benchmark",
        "benchmarks",
        "benches",
    }
)
_GENERATED_SUFFIXES = (
    ".min.js",
    ".bundle.js",
    ".pb.go",
)
_GENERATED_PATTERNS = (
    ".generated.",
    ".gen.",
    "_generated.",
    "_pb2.py",
    "_pb2_grpc.py",
)
_TEST_FILE_SUFFIXES = (
    "_test.py",
    "_test.go",
    "_test.rb",
    "_test.dart",
    "_spec.py",
    "_spec.rb",
)
_TEST_FILE_PREFIXES = (
    "test_",
    "spec_",
)


@dataclass(frozen=True)
class FileClassification:
    path: str
    language: str | None
    kind: str
    first_party: bool
    include_in_architecture: bool
    include_in_test_support: bool
    exclude_reason: str


def _normalize_segment(segment: str) -> str:
    raw = str(segment or "").strip().lower()
    return "".join(ch for ch in raw if ch.isalnum())


def _normalized_parts(path: Path) -> list[str]:
    return [_normalize_segment(part) for part in path.parts if part not in {"", ".", ".."}]


def _has_architecture_excluded_dir(path: Path) -> str:
    raw_parts = [part.lower() for part in path.parts[:-1]]
    normalized = _normalized_parts(path)[:-1]
    for raw, norm in zip(raw_parts, normalized):
        if raw in {".venv", "venv", "env"}:
            return "virtualenv"
        if raw in _ARCHITECTURE_EXCLUDED_DIRS or norm in _ARCHITECTURE_EXCLUDED_DIRS:
            return raw or norm or "excluded_dir"
    return ""


def _is_infra_path(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in {".tf", ".hcl"}:
        return True
    normalized = _normalized_parts(path)
    return any(part in _INFRA_DIR_MARKERS for part in normalized[:-1])


def _is_fixture_path(path: Path) -> bool:
    normalized = _normalized_parts(path)
    return any(part in _FIXTURE_DIR_MARKERS for part in normalized[:-1])


def _is_test_segment(segment: str) -> bool:
    norm = _normalize_segment(segment)
    if not norm:
        return False
    if norm in _TEST_SEGMENTS:
        return True
    return norm.endswith("tests") or norm.endswith("specs")


def _is_test_path(path: Path) -> bool:
    if any(_is_test_segment(part) for part in path.parts[:-1]):
        return True
    name = path.name.lower()
    if any(name.startswith(prefix) for prefix in _TEST_FILE_PREFIXES):
        return True
    if any(name.endswith(suffix) for suffix in _TEST_FILE_SUFFIXES):
        return True
    if ".test." in name or ".spec." in name:
        return True
    if name.endswith("test.php"):
        return True
    return False


def _is_generated_path(path: Path) -> bool:
    name = path.name.lower()
    if any(name.endswith(suffix) for suffix in _GENERATED_SUFFIXES):
        return True
    return any(pattern in name for pattern in _GENERATED_PATTERNS)


def classify_project_file(
    path: str | Path,
    *,
    rules: ArchitectureRules | None = None,
    project_root: Path | None = None,
) -> FileClassification:
    rel = Path(path)
    normalized = str(rel).replace("\\", "/").strip()
    probe = probe_file_language(rel, project_root=project_root)
    language = probe.language
    is_code = probe.is_code

    if not normalized:
        return FileClassification("", None, "ignored", False, False, False, "empty")
    if path_is_ignored(rel, rules):
        return FileClassification(normalized, language, "excluded", False, False, False, "architecture_rules")
    if is_hidden(rel):
        return FileClassification(normalized, language, "hidden", False, False, False, "hidden")
    if is_runtime_artifact(rel):
        return FileClassification(normalized, language, "runtime_artifact", False, False, False, "runtime_artifact")
    excluded_dir = _has_architecture_excluded_dir(rel)
    if excluded_dir:
        return FileClassification(normalized, language, "excluded", False, False, False, excluded_dir)
    if is_doc(rel):
        return FileClassification(normalized, language, "doc", True, False, False, "documentation")
    if _is_fixture_path(rel):
        return FileClassification(normalized, language, "fixture", True, False, False, "fixture")
    if _is_infra_path(rel):
        return FileClassification(normalized, language, "infra", True, False, False, "infrastructure")
    if _is_generated_path(rel):
        return FileClassification(normalized, language, "generated", True, False, False, "generated")
    if _is_test_path(rel):
        return FileClassification(normalized, language, "test", True, False, True, "test")
    if not is_code:
        return FileClassification(normalized, None, "ignored", True, False, False, "unsupported")
    return FileClassification(normalized, language, "source", True, True, False, "")


def should_include_architecture_file(
    path: str | Path,
    *,
    rules: ArchitectureRules | None = None,
    project_root: Path | None = None,
) -> bool:
    return classify_project_file(path, rules=rules, project_root=project_root).include_in_architecture


def should_include_test_support_file(
    path: str | Path,
    *,
    rules: ArchitectureRules | None = None,
    project_root: Path | None = None,
) -> bool:
    return classify_project_file(path, rules=rules, project_root=project_root).include_in_test_support


def should_include_tree_path(
    path: str | Path,
    *,
    rules: ArchitectureRules | None = None,
    project_root: Path | None = None,
) -> bool:
    rel = Path(path)
    if not str(rel).strip():
        return False
    if path_is_ignored(rel, rules):
        return False
    if is_hidden(rel) or is_runtime_artifact(rel):
        return False
    raw_parts = [part.lower() for part in rel.parts]
    normalized = _normalized_parts(rel)
    for raw, norm in zip(raw_parts, normalized):
        if raw in {".venv", "venv", "env"}:
            return False
        if raw in _ARCHITECTURE_EXCLUDED_DIRS or norm in _ARCHITECTURE_EXCLUDED_DIRS:
            return False
        if _is_test_segment(raw) or _is_test_segment(norm):
            return False
        if norm in _FIXTURE_DIR_MARKERS:
            return False
        if norm in _INFRA_DIR_MARKERS:
            return False
        if norm == "docs":
            return False
    if is_doc(rel):
        return False
    if rel.suffix:
        return should_include_architecture_file(rel, rules=rules, project_root=project_root)
    if project_root is None:
        return True
    return should_include_architecture_file(rel, rules=rules, project_root=project_root)


def build_file_manifest(target: Path, *, rules: ArchitectureRules | None = None) -> dict:
    effective_rules = rules or load_hippo_rules(target)
    files: dict[str, dict[str, object]] = {}
    for p in sorted(target.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(target)
        classified = classify_project_file(rel, rules=effective_rules, project_root=target)
        if classified.kind in {"ignored", "hidden", "runtime_artifact", "excluded", "doc", "fixture"}:
            continue
        files[classified.path] = asdict(classified)
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }


def write_file_manifest(output_dir: Path, manifest: dict) -> Path:
    out_path = output_dir / FILE_MANIFEST_FILE
    write_json(out_path, manifest)
    return out_path
