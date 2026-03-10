from __future__ import annotations

from hippocampus.tools.structure_prompt_project_map import (
    rank_entry_files,
    render_project_map,
    split_path,
)
from hippocampus.types import TreeNode


def test_split_path_and_rank_entry_files():
    files = {
        "app/main.py": {"role": "source", "score": 8.0},
        "app/cli.py": {"role": "source", "score": 6.0},
        "tests/test_app.py": {"role": "test", "score": 9.0},
    }
    assert split_path("app/main.py") == ("app", "main.py")
    ranked = rank_entry_files(files, archetype_entry_reasons={"main.py": "project entry"})
    assert ranked
    assert ranked[0][0] == "app/main.py"
    assert "entry" in ranked[0][1]


def test_render_project_map_smoke():
    root = TreeNode(
        id="dir:.",
        type="dir",
        name=".",
        children=[
            TreeNode(id="dir:app", type="dir", name="app", children=[]),
            TreeNode(id="dir:tests", type="dir", name="tests", children=[]),
        ],
    )
    files = {
        "app/main.py": {"role": "source", "score": 10.0},
        "app/service.py": {"role": "source", "score": 7.0},
        "tests/test_service.py": {"role": "test", "score": 3.0},
    }
    file_roles = {
        "app/main.py": "source",
        "app/service.py": "source",
        "tests/test_service.py": "test",
    }
    profile = {
        "name": "balanced",
        "llm_reading_items": 4,
        "llm_axes_items": 4,
        "llm_hotspots_items": 4,
    }
    text = render_project_map(
        {"architecture": "layered service"},
        root,
        files,
        file_roles,
        archetype="service",
        profile=profile,
        skip_dir_fn=lambda _name, _parts: False,
    )
    assert "Project Map" in text
    assert "Entry Points" in text
    assert "Fast Navigation Path" in text
