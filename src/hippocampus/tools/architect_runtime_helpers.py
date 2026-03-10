"""Runtime helpers for architect workflows."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from ..constants import INDEX_FILE
from ..utils import read_json
from .architect_models import RuleFinding, Severity


def run_git_capture(
    cmd: list[str],
    *,
    cwd: Optional[Path] = None,
    max_chars: int = 20000,
) -> str:
    """Run a git command and return stdout with truncation."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
            cwd=cwd,
        )
        output = result.stdout
        if len(output) > max_chars:
            output = output[:max_chars] + "\n... (truncated)"
        return output
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def compute_rule_score(findings: list[RuleFinding]) -> int:
    """Compute score: 100 - critical*20 - warning*5."""
    score = 100
    for finding in findings:
        if finding.severity == Severity.CRITICAL:
            score -= 20
        elif finding.severity == Severity.WARNING:
            score -= 5
    return max(0, score)


def load_index(output_dir: Path) -> dict:
    """Load hippocampus index from output directory."""
    index_path = output_dir / INDEX_FILE
    if not index_path.exists():
        raise FileNotFoundError(
            f"Index not found at {index_path}. Run 'hippo index' first."
        )
    return read_json(index_path)
