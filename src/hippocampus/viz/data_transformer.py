"""Visualization data transformer facade."""

from __future__ import annotations

from .data_transformer_dependency_graph import (
    transform_files_to_graph,
    transform_functions_to_graph,
)
from .data_transformer_module_graph import (
    ROLE_COLORS,
    calculate_ring_positions,
    calculate_role_positions,
    calculate_tiered_positions,
    compute_frame_diff,
    get_role_color,
    get_tier_color,
    transform_modules_to_graph,
    transform_snapshots_to_frames,
)
from .data_transformer_treemap_stats import (
    transform_files_to_treemap,
    transform_modules_to_treemap,
    transform_snapshots_to_trends,
    transform_stats_to_pie,
)

# Backward-compatible private aliases (legacy imports/tests).
_ROLE_COLORS = ROLE_COLORS
_get_tier_color = get_tier_color
_get_role_color = get_role_color
_calculate_ring_positions = calculate_ring_positions
_calculate_role_positions = calculate_role_positions
_calculate_tiered_positions = calculate_tiered_positions
_compute_frame_diff = compute_frame_diff

__all__ = [
    "transform_modules_to_graph",
    "transform_files_to_graph",
    "transform_functions_to_graph",
    "transform_files_to_treemap",
    "transform_modules_to_treemap",
    "transform_stats_to_pie",
    "transform_snapshots_to_trends",
    "transform_snapshots_to_frames",
]
