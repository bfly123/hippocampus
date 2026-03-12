"""Tools subpackage.

This package keeps backward-compatible module names at the package root while
organizing implementations into focused subpackages.
"""

from __future__ import annotations

import sys
from importlib import import_module

_LEGACY_SUBMODULE_ALIASES = {
    "architect": "architect.architect",
    "architect_llm": "architect.architect_llm",
    "architect_models": "architect.architect_models",
    "architect_rules": "architect.architect_rules",
    "architect_runtime": "architect.architect_runtime",
    "architect_runtime_helpers": "architect.architect_runtime_helpers",
    "index_gen": "index.index_gen",
    "index_gen_cache": "index.index_gen_cache",
    "index_gen_dependencies": "index.index_gen_dependencies",
    "index_gen_local": "index.index_gen_local",
    "index_gen_phase1": "index.index_gen_phase1",
    "index_gen_phase1_runner": "index.index_gen_phase1_runner",
    "index_gen_phase2": "index.index_gen_phase2",
    "index_gen_phase2_incremental": "index.index_gen_phase2_incremental",
    "index_gen_phase3": "index.index_gen_phase3",
    "index_gen_phase4": "index.index_gen_phase4",
    "index_gen_reporting": "index.index_gen_reporting",
    "index_gen_runtime": "index.index_gen_runtime",
    "ranker": "ranker.ranker",
    "ranker_common": "ranker.ranker_common",
    "ranker_graph": "ranker.ranker_graph",
    "ranker_heuristic": "ranker.ranker_heuristic",
    "ranker_symbol": "ranker.ranker_symbol",
    "structure_prompt": "structure.structure_prompt",
    "structure_prompt_budget": "structure.structure_prompt_budget",
    "structure_prompt_navigation": "structure.structure_prompt_navigation",
    "structure_prompt_profiles": "structure.structure_prompt_profiles",
    "structure_prompt_project_map": "structure.structure_prompt_project_map",
    "structure_prompt_project_map_boundaries": "structure.structure_prompt_project_map_boundaries",
    "structure_prompt_project_map_brief": "structure.structure_prompt_project_map_brief",
    "structure_prompt_project_map_paths": "structure.structure_prompt_project_map_paths",
    "structure_prompt_ranking": "structure.structure_prompt_ranking",
    "structure_prompt_roles": "structure.structure_prompt_roles",
    "structure_prompt_runner": "structure.structure_prompt_runner",
    "structure_prompt_sections": "structure.structure_prompt_sections",
    "structure_prompt_tree": "structure.structure_prompt_tree",
    "structure_strategy": "structure.structure_strategy",
}

for legacy_name, current_name in _LEGACY_SUBMODULE_ALIASES.items():
    module = import_module(f"{__name__}.{current_name}")
    sys.modules.setdefault(f"{__name__}.{legacy_name}", module)
    globals().setdefault(legacy_name, module)

__all__ = sorted(_LEGACY_SUBMODULE_ALIASES)
