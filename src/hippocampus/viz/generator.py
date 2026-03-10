"""HTML visualization generator."""

import json
from pathlib import Path
from typing import Optional

from .data_transformer import (
    transform_modules_to_graph,
    transform_files_to_graph,
    transform_functions_to_graph,
    transform_files_to_treemap,
    transform_modules_to_treemap,
    transform_stats_to_pie,
    transform_snapshots_to_trends,
    transform_snapshots_to_frames
)
from .templates import HTML_HEADER


def load_json_file(file_path: Path) -> dict:
    """Load JSON file safely."""
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Warning: Failed to load {file_path}: {e}")
        return {}


def generate_viz_html(
    output_dir: Path,
    verbose: bool = False
) -> Path:
    """Generate interactive visualization HTML.

    Args:
        output_dir: Directory containing hippocampus data files
        verbose: Enable verbose output

    Returns:
        Path to generated HTML file
    """
    if verbose:
        print("Loading data files...")

    # Load data sources
    index = load_json_file(output_dir / "hippocampus-index.json")
    tree = load_json_file(output_dir / "tree.json")

    if not index:
        raise FileNotFoundError(f"hippocampus-index.json not found in {output_dir}")

    if verbose:
        print("Transforming data...")

    # Transform data
    modules_graph = transform_modules_to_graph(index)
    files_graph = transform_files_to_graph(index)
    functions_graph = transform_functions_to_graph(index)
    files_treemap = transform_files_to_treemap(tree) if tree else {}
    modules_treemap = transform_modules_to_treemap(index)
    stats_pie = transform_stats_to_pie(index)
    trends = transform_snapshots_to_trends(output_dir / "snapshots")
    snapshots_frames = transform_snapshots_to_frames(output_dir / "snapshots")

    if verbose:
        print("Rendering HTML template...")

    # Render HTML with string replacement
    html = HTML_HEADER
    html = html.replace("__INDEX_DATA__", json.dumps(index, ensure_ascii=False))
    html = html.replace("__MODULES_GRAPH__", json.dumps(modules_graph, ensure_ascii=False))
    html = html.replace("__FILES_GRAPH__", json.dumps(files_graph, ensure_ascii=False))
    html = html.replace("__FUNCTIONS_GRAPH__", json.dumps(functions_graph, ensure_ascii=False))
    html = html.replace("__FILES_TREEMAP__", json.dumps(files_treemap, ensure_ascii=False))
    html = html.replace("__MODULES_TREEMAP__", json.dumps(modules_treemap, ensure_ascii=False))
    html = html.replace("__STATS_PIE__", json.dumps(stats_pie, ensure_ascii=False))
    html = html.replace("__TRENDS__", json.dumps(trends, ensure_ascii=False))
    html = html.replace("__SNAPSHOTS_DATA__", json.dumps(snapshots_frames, ensure_ascii=False))

    # Write output
    output_path = output_dir / "hippocampus-viz.html"
    output_path.write_text(html, encoding="utf-8")

    if verbose:
        print(f"Generated: {output_path}")

    return output_path
