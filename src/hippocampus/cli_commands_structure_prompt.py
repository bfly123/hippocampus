from __future__ import annotations

from pathlib import Path

import click

from .config import load_config
from .constants import CONFIG_FILE, HIPPO_DIR, STRUCTURE_PROMPT_FILE


def register_structure_prompt_commands(cli) -> dict[str, object]:
    @cli.command("structure-prompt")
    @click.option("--target", default=".", help="Project root directory.")
    @click.option(
        "--max-tokens",
        type=click.IntRange(min=1),
        default=None,
        help="Max token budget (default: from config)",
    )
    @click.option(
        "--profile",
        type=click.Choice(["auto", "map", "deep"]),
        default=None,
        help="Render profile (default: from config).",
    )
    @click.option(
        "--output-name",
        default=None,
        help="Output filename under .hippocampus/ (default: structure-prompt.md).",
    )
    @click.option(
        "--llm-enhance/--no-llm-enhance",
        default=None,
        help="Enable LLM navigation brief enhancement (default: from config).",
    )
    @click.pass_context
    def structure_prompt(ctx, target, max_tokens, profile, output_name, llm_enhance):
        """Generate structure prompt → structure-prompt.md."""
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR
        cfg_path = Path(ctx.obj["config_path"]) if ctx.obj["config_path"] else out / CONFIG_FILE
        cfg = load_config(cfg_path if cfg_path.exists() else None)

        if profile is None:
            raw_profile = str(getattr(cfg, "structure_prompt_profile", "auto")).strip().lower()
            profile = raw_profile if raw_profile in {"auto", "map", "deep"} else "auto"

        if max_tokens is None:
            if profile == "map":
                max_tokens = max(1, cfg.structure_prompt_map_tokens)
            elif profile == "deep":
                max_tokens = max(1, cfg.structure_prompt_deep_tokens)
            else:
                max_tokens = max(1, cfg.structure_prompt_max_tokens)

        from .tools.structure_prompt import run_structure_prompt

        if llm_enhance is None:
            llm_enhance = cfg.structure_prompt_llm_enhance

        if not ctx.obj["quiet"]:
            click.echo(
                "Generating structure prompt "
                f"(profile={profile}, max_tokens={max_tokens}, llm_enhance={llm_enhance}, "
                f"output={output_name or 'structure-prompt.md'}) ..."
            )
        md = run_structure_prompt(
            out,
            max_tokens=max_tokens,
            verbose=ctx.obj["verbose"],
            config=cfg,
            llm_enhance=llm_enhance,
            render_profile=profile,
            output_name=output_name,
        )
        if not ctx.obj["quiet"]:
            click.echo(f"Done: {len(md)} chars.")

    @cli.command("structure-prompt-all")
    @click.option("--target", default=".", help="Project root directory.")
    @click.option(
        "--map-tokens",
        type=click.IntRange(min=1),
        default=None,
        help="Token budget for map profile.",
    )
    @click.option(
        "--deep-tokens",
        type=click.IntRange(min=1),
        default=None,
        help="Token budget for deep profile.",
    )
    @click.option(
        "--set-default",
        type=click.Choice(["map", "deep", "keep"]),
        default="map",
        help="Which generated file to copy to structure-prompt.md.",
    )
    @click.option(
        "--llm-enhance/--no-llm-enhance",
        default=None,
        help="Enable LLM navigation brief enhancement (default: from config).",
    )
    @click.pass_context
    def structure_prompt_all(ctx, target, map_tokens, deep_tokens, set_default, llm_enhance):
        """Generate map + deep structure prompts in one run."""
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR
        cfg_path = Path(ctx.obj["config_path"]) if ctx.obj["config_path"] else out / CONFIG_FILE
        cfg = load_config(cfg_path if cfg_path.exists() else None)

        if map_tokens is None:
            map_tokens = max(1, cfg.structure_prompt_map_tokens)
        if deep_tokens is None:
            deep_tokens = max(1, cfg.structure_prompt_deep_tokens)
        if llm_enhance is None:
            llm_enhance = cfg.structure_prompt_llm_enhance

        from .tools.structure_prompt import run_structure_prompt

        map_name = "structure-prompt-map.md"
        deep_name = "structure-prompt-deep.md"

        if not ctx.obj["quiet"]:
            click.echo(
                "Generating structure prompts "
                f"(map={map_tokens}, deep={deep_tokens}, llm_enhance={llm_enhance}) ..."
            )

        map_md = run_structure_prompt(
            out,
            max_tokens=map_tokens,
            verbose=ctx.obj["verbose"],
            config=cfg,
            llm_enhance=llm_enhance,
            render_profile="map",
            output_name=map_name,
        )
        deep_md = run_structure_prompt(
            out,
            max_tokens=deep_tokens,
            verbose=ctx.obj["verbose"],
            config=cfg,
            llm_enhance=llm_enhance,
            render_profile="deep",
            output_name=deep_name,
        )

        if set_default != "keep":
            default_path = out / STRUCTURE_PROMPT_FILE
            source_md = map_md if set_default == "map" else deep_md
            default_path.write_text(source_md, encoding="utf-8")

        if not ctx.obj["quiet"]:
            click.echo(
                f"Done: {map_name}={len(map_md)} chars, {deep_name}={len(deep_md)} chars, "
                f"default={set_default}"
            )

    return {
        "structure-prompt": structure_prompt,
        "structure-prompt-all": structure_prompt_all,
    }


__all__ = ["register_structure_prompt_commands"]
