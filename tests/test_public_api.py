from hippocampus import (
    initialize_project,
    navigate,
    navigate_context_pack,
    render_context_snippets,
    summarize_project_index,
)
from hippocampus.nav import NavigateResult


def test_initialize_project_creates_output_dir(tmp_path):
    hippo_dir = initialize_project(tmp_path)
    assert hippo_dir == tmp_path / ".hippocampus"
    assert hippo_dir.is_dir()


def test_navigate_delegates_to_public_navigation(monkeypatch, tmp_path):
    called = {}

    def _stub(**kwargs):
        called.update(kwargs)
        return NavigateResult(ranked_files=[{"file": "src/router.py", "rank": 1.0, "tier": 1}])

    monkeypatch.setattr("hippocampus.api.navigate_codebase", _stub)
    result = navigate("find router", target=tmp_path, budget_tokens=123, conversation_files=["src/router.py"])

    assert isinstance(result, NavigateResult)
    assert called["query"] == "find router"
    assert called["budget_tokens"] == 123
    assert called["conversation_files"] == ["src/router.py"]
    assert called["hippo_dir"] == tmp_path / ".hippocampus"


def test_public_support_helpers_are_exported():
    assert callable(navigate_context_pack)
    assert callable(render_context_snippets)
    assert callable(summarize_project_index)
