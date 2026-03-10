from __future__ import annotations

from hippocampus.cli_pipeline_helpers import (
    build_ranked_tag_report,
    format_ranked_tag_line,
    run_pipeline_steps,
)


def test_format_ranked_tag_line_variants():
    line_full = format_ranked_tag_line(1, ("a.py", "a.py", 10, "func", "def"))
    assert "a.py" in line_full
    assert "func" in line_full

    line_single = format_ranked_tag_line(2, ("b.py",))
    assert "b.py" in line_single
    assert "(no symbols)" in line_single

    line_fallback = format_ranked_tag_line(3, ("x", "y"))
    assert "('x', 'y')" in line_fallback


def test_build_ranked_tag_report_has_summary_lines():
    ranked_tags = [
        ("a.py", "a.py", 10, "func", "def"),
        ("b.py",),
        ("c.py", "c.py", 2, "X", "class"),
    ]
    lines = build_ranked_tag_report(ranked_tags, limit=2, file_count=2)
    text = "\n".join(lines)
    assert "Symbol ranking for 2 file(s):" in text
    assert "... and 1 more symbols" in text
    assert "Total symbols: 3" in text


def test_run_pipeline_steps_orders_invocations_and_messages():
    class DummyCtx:
        def __init__(self):
            self.calls = []

        def invoke(self, command, **kwargs):
            self.calls.append((command.__name__, kwargs))

    def cmd_a():
        return None

    def cmd_b():
        return None

    messages: list[str] = []
    ctx = DummyCtx()
    run_pipeline_steps(
        ctx=ctx,
        quiet=False,
        echo=messages.append,
        steps=(
            ("Step A", cmd_a, {"x": 1}),
            ("Step B", cmd_b, {"y": 2}),
        ),
    )

    assert ctx.calls == [("cmd_a", {"x": 1}), ("cmd_b", {"y": 2})]
    assert messages[0] == "=== Step A ==="
    assert messages[1] == "=== Step B ==="
    assert messages[-1] == "=== Pipeline complete ==="

