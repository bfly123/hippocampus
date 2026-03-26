from __future__ import annotations

from .pipeline_command_builders import (
    build_generate_command,
    build_index_command,
    build_refresh_command,
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
    generate = build_generate_command(command_refs=command_refs, run_cmd=run)
    update = build_update_command(
        command_refs=command_refs,
        trim_cmd=trim,
        index_cmd=index,
    )
    refresh = build_refresh_command(update_cmd=update)

    cli.add_command(repomap)
    cli.add_command(trim)
    cli.add_command(index)
    cli.add_command(run)
    cli.add_command(generate)
    cli.add_command(update)
    cli.add_command(refresh)

    return {
        "repomap": repomap,
        "trim": trim,
        "index": index,
        "run": run,
        "_generate": generate,
        "update": update,
        "refresh": refresh,
    }


__all__ = ["register_pipeline_commands"]
