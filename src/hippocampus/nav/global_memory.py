"""
Global memory integration - loads module scores from hippocampus index.

Provides file-level priors based on module importance scores.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Set, Optional

from ..utils import read_json


def load_module_scores(index_path: Path) -> Dict[str, float]:
    """
    Load module importance scores from hippocampus-index.json.

    Args:
        index_path: Path to index file

    Returns:
        Dict of {module_id: core_score}
    """
    try:
        index = read_json(index_path)
        return {
            mod["id"]: mod.get("core_score", 0.0)
            for mod in index.get("modules", [])
        }
    except Exception:
        return {}


def build_file_to_module_map(index_path: Path) -> Dict[str, str]:
    """
    Build file path to module ID mapping.

    Args:
        index_path: Path to index file

    Returns:
        Dict of {file_path: module_id}
    """
    try:
        index = read_json(index_path)
        return {
            path: file_info["module"]
            for path, file_info in index.get("files", {}).items()
            if "module" in file_info
        }
    except Exception:
        return {}


def compute_file_priors(
    all_files: Set[str],
    module_scores: Dict[str, float],
    file_to_module: Dict[str, str]
) -> Dict[str, float]:
    """
    Compute file-level prior weights from module scores.

    Args:
        all_files: All tracked files
        module_scores: Module importance scores
        file_to_module: File to module mapping

    Returns:
        Dict of {file: prior_weight} (normalized)
    """
    priors = {}
    for file in all_files:
        module = file_to_module.get(file)
        if module:
            priors[file] = module_scores.get(module, 1.0)
        else:
            priors[file] = 1.0

    # Normalize
    total = sum(priors.values())
    if total > 0:
        return {f: w / total for f, w in priors.items()}
    return priors
