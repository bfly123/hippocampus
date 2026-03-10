"""Module-level core_score computation.

Scores each module by relative importance using:
  0.45 × code_ratio  (lines of signatures as proxy for code volume)
  0.10 × file_ratio  (fraction of total files)
  0.45 × role_bonus  (based on dominant tag role)

Tier classification:
  score >= 0.30  → "core"
  score >= 0.10  → "secondary"
  score <  0.10  → "peripheral"

Safety rule: modules with >= 70% test files cannot be "core".

Functional role classification:
  core      — core business logic
  infra     — infrastructure / support
  interface — user-facing entry points
  test      — test code
  docs      — documentation (reserved)
"""

from __future__ import annotations

import re
from typing import Any


# ── Per-file viz role classification (path-first + tag fallback) ──

# Path patterns → role (first match wins)
_PATH_ROLE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # test files
    (re.compile(r"(^|/)tests?/"), "test"),
    (re.compile(r"(^|/)test_[^/]*$"), "test"),
    (re.compile(r"_test\.py$"), "test"),
    (re.compile(r"_spec\.py$"), "test"),
    (re.compile(r"(^|/)conftest\."), "test"),
    # docs
    (re.compile(r"\.md$", re.IGNORECASE), "docs"),
    (re.compile(r"(^|/)docs/"), "docs"),
    (re.compile(r"(^|/)README", re.IGNORECASE), "docs"),
    (re.compile(r"(^|/)LICENSE", re.IGNORECASE), "docs"),
    (re.compile(r"(^|/)CHANGELOG", re.IGNORECASE), "docs"),
    # infra / config
    (re.compile(r"\.(yml|yaml|toml|cfg|ini)$"), "infra"),
    (re.compile(r"(^|/)setup\.[^/]*$"), "infra"),
    (re.compile(r"(^|/)Makefile$"), "infra"),
    (re.compile(r"(^|/)Dockerfile"), "infra"),
    (re.compile(r"(^|/)\.env"), "infra"),
    # interface
    (re.compile(r"(^|/)cli/"), "interface"),
    (re.compile(r"(^|/)mcp/"), "interface"),
    (re.compile(r"(^|/)viz/"), "interface"),
    (re.compile(r"(^|/)ui/"), "interface"),
    (re.compile(r"(^|/)web/"), "interface"),
]

# Tag keywords → role (first match wins, checked only when path gives no match)
_TAG_ROLE_RULES: list[tuple[set[str], str]] = [
    ({"test", "spec", "mock"}, "test"),
    ({"entrypoint", "cli", "ui", "mcp", "web"}, "interface"),
    ({"config", "setup", "ci", "adapter", "util", "helper"}, "infra"),
    ({"docs", "asset"}, "docs"),
]

# Tiebreak priority: lower index wins
_ROLE_TIEBREAK = ["core", "interface", "infra", "test", "docs"]


def _classify_file_viz_role(file_path: str, file_data: dict) -> str:
    """Classify a single file's functional role using path-first + tag fallback.

    Args:
        file_path: Relative file path (e.g. "tests/test_engine.py")
        file_data: File dict from the index

    Returns:
        One of: "core", "infra", "interface", "test", "docs"
    """
    # 1. Path-based rules (first match wins)
    for pattern, role in _PATH_ROLE_PATTERNS:
        if pattern.search(file_path):
            return role

    # 2. Tag-based fallback
    tags = file_data.get("tags", [])
    for keywords, role in _TAG_ROLE_RULES:
        for tag in tags:
            if tag.lower() in keywords:
                return role

    return "core"


def _classify_module_role(
    module_id: str, module_files: list[tuple[str, dict]]
) -> str:
    """Classify a module's functional role via per-file voting.

    Args:
        module_id: The module identifier (e.g. "mod:testing")
        module_files: List of (file_path, file_data) tuples

    Returns:
        One of: "core", "infra", "interface", "test", "docs"
    """
    if not module_files:
        return "core"

    # Per-file voting
    votes: dict[str, int] = {}
    for fpath, fdata in module_files:
        role = _classify_file_viz_role(fpath, fdata)
        votes[role] = votes.get(role, 0) + 1

    if not votes:
        return "core"

    # Majority vote with tiebreak
    max_count = max(votes.values())
    candidates = [role for role, count in votes.items() if count == max_count]

    if len(candidates) == 1:
        return candidates[0]

    for role in _ROLE_TIEBREAK:
        if role in candidates:
            return role

    return "core"


# Role bonus mapping: tag substring → bonus value.
# Checked in order; first match wins per file.
_ROLE_BONUS: list[tuple[str, float]] = [
    ("entrypoint", 1.0),
    ("entry", 1.0),
    ("main", 1.0),
    ("api", 0.8),
    ("lib", 0.8),
    ("core", 0.8),
    ("service", 0.8),
    ("util", 0.6),
    ("helper", 0.6),
    ("config", 0.4),
    ("setup", 0.4),
    ("test", 0.2),
    ("spec", 0.2),
    ("mock", 0.2),
]

# Tier thresholds
_CORE_THRESHOLD = 0.30
_SECONDARY_THRESHOLD = 0.10


def _file_role_bonus(tags: list[str]) -> float:
    """Return the highest role bonus matched from a file's tags."""
    for tag in tags:
        tag_lower = tag.lower()
        for keyword, bonus in _ROLE_BONUS:
            if keyword in tag_lower:
                return bonus
    return 0.0


def _classify_tier(score: float, test_file_ratio: float = 0.0) -> str:
    """Classify module tier based on score and test file ratio.

    Args:
        score: Computed module score
        test_file_ratio: Fraction of files in module that are test files

    Returns:
        Tier classification string
    """
    # Safety rule: modules with >= 70% test files cannot be "core"
    if test_file_ratio >= 0.7 and score >= _CORE_THRESHOLD:
        return "secondary"

    if score >= _CORE_THRESHOLD:
        return "core"
    if score >= _SECONDARY_THRESHOLD:
        return "secondary"
    return "peripheral"


def compute_module_scores(index: dict[str, Any]) -> dict[str, Any]:
    """Compute core_score and tier for each module in the index.

    Mutates the index in-place (adds fields to each module dict)
    and returns the index for convenience.
    """
    modules: list[dict] = index.get("modules", [])
    files: dict[str, dict] = index.get("files", {})

    if not modules or not files:
        return index

    total_files = len(files)
    total_sigs = sum(len(f.get("signatures", [])) for f in files.values())

    # Group files by module: mid → [(file_path, file_data), ...]
    module_files: dict[str, list[tuple[str, dict]]] = {}
    for fpath, fdata in files.items():
        mid = fdata.get("module", "")
        if mid:
            module_files.setdefault(mid, []).append((fpath, fdata))

    for mod in modules:
        mid = mod["id"]
        mfiles = module_files.get(mid, [])

        # file_ratio: fraction of project files in this module
        file_ratio = len(mfiles) / total_files if total_files else 0.0

        # code_ratio: fraction of total signatures in this module
        mod_sigs = sum(len(f.get("signatures", [])) for _, f in mfiles)
        code_ratio = mod_sigs / total_sigs if total_sigs else 0.0

        # role_bonus: average of per-file role bonuses
        if mfiles:
            bonuses = [_file_role_bonus(f.get("tags", [])) for _, f in mfiles]
            role_bonus = sum(bonuses) / len(bonuses)
        else:
            role_bonus = 0.0

        score = 0.45 * code_ratio + 0.10 * file_ratio + 0.45 * role_bonus
        # Normalize: cap at 1.0 (shouldn't exceed, but be safe)
        score = min(score, 1.0)

        # Calculate test file ratio for safety rule (consistent with path-driven role)
        test_file_count = sum(
            1 for fp, fd in mfiles
            if _classify_file_viz_role(fp, fd) == "test"
        )
        test_file_ratio = test_file_count / len(mfiles) if mfiles else 0.0

        mod["core_score"] = round(score, 4)
        mod["tier"] = _classify_tier(score, test_file_ratio)
        mod["role"] = _classify_module_role(mid, mfiles)

    return index
