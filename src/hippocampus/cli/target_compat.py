from __future__ import annotations

import click


def target_option_alias():
    return click.option(
        "--target",
        "target_option",
        default=None,
        hidden=True,
        help="Project root directory.",
    )


def resolve_target_value(target: str | None, target_option: str | None) -> str:
    resolved = str(target_option or target or ".").strip()
    return resolved or "."


__all__ = ["resolve_target_value", "target_option_alias"]
