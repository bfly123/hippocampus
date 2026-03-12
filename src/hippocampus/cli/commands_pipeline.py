from __future__ import annotations

from .pipeline_command_builders import (
    build_index_command,
    build_repomap_command,
    build_run_command,
    build_trim_command,
)


def register_pipeline_commands(cli, command_refs: dict[str, object]) -> dict[str, object]:
    repomap = build_repomap_command()
    trim = build_trim_command()
    index = build_index_command()
    run = build_run_command(command_refs=command_refs, trim_cmd=trim, index_cmd=index)

    cli.add_command(repomap)
    cli.add_command(trim)
    cli.add_command(index)
    cli.add_command(run)

    return {
        "repomap": repomap,
        "trim": trim,
        "index": index,
        "run": run,
    }


__all__ = ["register_pipeline_commands"]
