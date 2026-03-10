"""Repomix subprocess wrapper — calls repomix CLI and parses JSON output."""

from __future__ import annotations

import json
import subprocess
import shutil
from pathlib import Path


def find_repomix() -> str | None:
    """Find the repomix executable."""
    return shutil.which("repomix")


def run_repomix_structure(target: Path, output_path: Path) -> dict:
    """Run repomix in structure-only mode, return parsed JSON."""
    exe = find_repomix()
    if not exe:
        raise FileNotFoundError("repomix not found in PATH")

    cmd = [
        exe,
        "--style", "json",
        "--no-files",
        "--include-full-directory-structure",
        "--ignore", ".*,.*/**",
        "-o", str(output_path),
    ]
    subprocess.run(
        cmd, cwd=str(target),
        capture_output=True, text=True, check=True,
    )
    with open(output_path, encoding="utf-8") as f:
        return json.load(f)


def run_repomix_compress(target: Path, output_path: Path) -> dict:
    """Run repomix in compress mode, return parsed JSON."""
    exe = find_repomix()
    if not exe:
        raise FileNotFoundError("repomix not found in PATH")

    cmd = [
        exe,
        "--style", "json",
        "--compress",
        "--ignore", ".*,.*/**",
        "-o", str(output_path),
    ]
    subprocess.run(
        cmd, cwd=str(target),
        capture_output=True, text=True, check=True,
    )
    with open(output_path, encoding="utf-8") as f:
        return json.load(f)
