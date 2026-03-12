from __future__ import annotations

from .pipeline_command_builders import (
    build_index_command,
    build_onekey_command,
    build_repomap_command,
    build_run_command,
    build_trim_command,
    build_update_command,
)


def register_pipeline_commands(cli, command_refs: dict[str, object]) -> dict[str, object]:
    repomap = build_repomap_command()
    trim = build_trim_command()
    index = build_index_command()
    run = build_run_command(command_refs=command_refs, trim_cmd=trim, index_cmd=index)
    onekey = build_onekey_command(command_refs=command_refs, run_cmd=run)
    update = build_update_command(
        command_refs=command_refs,
        trim_cmd=trim,
        index_cmd=index,
    )

    cli.add_command(repomap)
    cli.add_command(trim)
    cli.add_command(index)
    cli.add_command(run)
    cli.add_command(onekey)
    cli.add_command(update)

    return {
        "repomap": repomap,
        "trim": trim,
        "index": index,
        "run": run,
        "onekey": onekey,
        "update": update,
    }


__all__ = ["register_pipeline_commands"]
