from __future__ import annotations

from pathlib import Path

import click

from ..config import load_config
from ..constants import CONFIG_FILE, HIPPO_DIR, STRUCTURE_PROMPT_FILE


def _resolve_config_for_target(ctx, target: Path):
    out = target / HIPPO_DIR
    raw_cfg_path = ctx.obj["config_path"]
    cfg_path = Path(raw_cfg_path) if raw_cfg_path else out / CONFIG_FILE
    config = load_config(cfg_path if cfg_path.exists() else None, project_root=target)
    return out, config


def _resolved_profile(cfg, profile: str | None) -> str:
    if profile is not None:
        return profile
    raw_profile = str(getattr(cfg, "structure_prompt_profile", "auto")).strip().lower()
    return raw_profile if raw_profile in {"auto", "map", "deep"} else "auto"


def _resolved_token_budget(cfg, profile: str, override: int | None) -> int:
    if override is not None:
        return override
    token_by_profile = {
        "map": cfg.structure_prompt_map_tokens,
        "deep": cfg.structure_prompt_deep_tokens,
        "auto": cfg.structure_prompt_max_tokens,
    }
    return max(1, token_by_profile.get(profile, cfg.structure_prompt_max_tokens))


def _echo_unless_quiet(ctx, message: str) -> None:
    if not ctx.obj["quiet"]:
        click.echo(message)


def _run_prompt(out: Path, *, ctx, cfg, max_tokens: int, llm_enhance: bool, profile: str, output_name: str | None):
    from ..tools.structure_prompt import run_structure_prompt

    return run_structure_prompt(
        out,
        max_tokens=max_tokens,
        verbose=ctx.obj["verbose"],
        config=cfg,
        llm_enhance=llm_enhance,
        render_profile=profile,
        output_name=output_name,
    )


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
        out, cfg = _resolve_config_for_target(ctx, tgt)
        resolved_profile = _resolved_profile(cfg, profile)
        resolved_tokens = _resolved_token_budget(cfg, resolved_profile, max_tokens)
        resolved_llm_enhance = (
            cfg.structure_prompt_llm_enhance if llm_enhance is None else llm_enhance
        )

        _echo_unless_quiet(
            ctx,
            "Generating structure prompt "
            f"(profile={resolved_profile}, max_tokens={resolved_tokens}, "
            f"llm_enhance={resolved_llm_enhance}, output={output_name or 'structure-prompt.md'}) ...",
        )
        md = _run_prompt(
            out,
            ctx=ctx,
            cfg=cfg,
            max_tokens=resolved_tokens,
            llm_enhance=resolved_llm_enhance,
            profile=resolved_profile,
            output_name=output_name,
        )
        _echo_unless_quiet(ctx, f"Done: {len(md)} chars.")

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
        out, cfg = _resolve_config_for_target(ctx, tgt)
        resolved_map_tokens = _resolved_token_budget(cfg, "map", map_tokens)
        resolved_deep_tokens = _resolved_token_budget(cfg, "deep", deep_tokens)
        resolved_llm_enhance = (
            cfg.structure_prompt_llm_enhance if llm_enhance is None else llm_enhance
        )
        map_name = "structure-prompt-map.md"
        deep_name = "structure-prompt-deep.md"

        _echo_unless_quiet(
            ctx,
            "Generating structure prompts "
            f"(map={resolved_map_tokens}, deep={resolved_deep_tokens}, "
            f"llm_enhance={resolved_llm_enhance}) ...",
        )
        map_md = _run_prompt(
            out,
            ctx=ctx,
            cfg=cfg,
            max_tokens=resolved_map_tokens,
            llm_enhance=resolved_llm_enhance,
            profile="map",
            output_name=map_name,
        )
        deep_md = _run_prompt(
            out,
            ctx=ctx,
            cfg=cfg,
            max_tokens=resolved_deep_tokens,
            llm_enhance=resolved_llm_enhance,
            profile="deep",
            output_name=deep_name,
        )

        if set_default != "keep":
            default_path = out / STRUCTURE_PROMPT_FILE
            source_md = map_md if set_default == "map" else deep_md
            default_path.write_text(source_md, encoding="utf-8")

        _echo_unless_quiet(
            ctx,
            f"Done: {map_name}={len(map_md)} chars, {deep_name}={len(deep_md)} chars, "
            f"default={set_default}",
        )

    return {
        "structure-prompt": structure_prompt,
        "structure-prompt-all": structure_prompt_all,
    }


__all__ = ["register_structure_prompt_commands"]
