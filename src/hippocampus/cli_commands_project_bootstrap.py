from __future__ import annotations

import shutil
from pathlib import Path

import click

from .config import default_config_yaml, load_config
from .constants import CONFIG_FILE, HIPPO_DIR, QUERIES_DIR, VENDOR_QUERIES_REL
from .resources import copy_packaged_queries


def _resolve_paths(config_path, output_dir, target):
    """Resolve config, output dir, and target from CLI options."""
    if config_path:
        cfg_path = Path(config_path)
    else:
        cfg_path = Path(HIPPO_DIR) / CONFIG_FILE

    tgt_hint = Path(target).resolve() if target else None
    cfg = load_config(cfg_path if cfg_path.exists() else None, project_root=tgt_hint)

    if output_dir:
        out = Path(output_dir)
    else:
        out = Path(cfg.output_dir)

    if target:
        tgt = Path(target)
    else:
        tgt = Path(cfg.target)

    return cfg, out, tgt


def register_project_bootstrap_commands(cli) -> dict[str, object]:
    @cli.command()
    @click.option("--target", default=".", help="Project root directory.")
    @click.pass_context
    def init(ctx, target):
        """Initialize .hippocampus/ directory with default config."""
        target = Path(target).resolve()
        hippo_dir = target / HIPPO_DIR
        hippo_dir.mkdir(parents=True, exist_ok=True)

        config_file = hippo_dir / CONFIG_FILE
        if not config_file.exists():
            config_file.write_text(default_config_yaml(), encoding="utf-8")
            click.echo(f"Created {config_file}")
        else:
            click.echo(f"Config already exists: {config_file}")

        queries_dst = hippo_dir / QUERIES_DIR
        queries_dst.mkdir(parents=True, exist_ok=True)

        vendor_src = target / VENDOR_QUERIES_REL
        if not vendor_src.exists():
            vendor_src = Path.cwd() / VENDOR_QUERIES_REL
        if not vendor_src.exists():
            pkg_root = Path(__file__).resolve().parent.parent.parent
            vendor_src = pkg_root / VENDOR_QUERIES_REL

        if vendor_src.exists():
            copied = 0
            for scm in vendor_src.glob("*.scm"):
                dst = queries_dst / scm.name
                if not dst.exists():
                    shutil.copy2(scm, dst)
                    copied += 1
            click.echo(f"Copied {copied} query files to {queries_dst}")
        else:
            copied = copy_packaged_queries(queries_dst)
            if copied:
                click.echo(f"Copied {copied} packaged query files to {queries_dst}")
            else:
                click.echo("Warning: query files not found, skipping .scm copy.")

        click.echo(f"Initialized {hippo_dir}")

    @cli.command("sig-extract")
    @click.option("--target", default=".", help="Project root directory.")
    @click.pass_context
    def sig_extract(ctx, target):
        """Extract code signatures → code-signatures.json."""
        _cfg, _out, _tgt = _resolve_paths(
            ctx.obj["config_path"], ctx.obj["output_dir"], target,
        )
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR
        out.mkdir(parents=True, exist_ok=True)

        from .tools.sig_extract import run_sig_extract

        if not ctx.obj["quiet"]:
            click.echo(f"Extracting signatures from {tgt} ...")
        doc = run_sig_extract(tgt, out, verbose=ctx.obj["verbose"])
        n_files = len(doc.files)
        n_sigs = sum(len(f.signatures) for f in doc.files.values())
        if not ctx.obj["quiet"]:
            click.echo(f"Done: {n_files} files, {n_sigs} signatures.")

    @cli.command("tree")
    @click.option("--target", default=".", help="Project root directory.")
    @click.pass_context
    def tree(ctx, target):
        """Generate structure tree → tree.json."""
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR
        out.mkdir(parents=True, exist_ok=True)

        from .tools.tree_gen import run_tree_gen

        if not ctx.obj["quiet"]:
            click.echo(f"Generating tree from {tgt} ...")
        doc = run_tree_gen(tgt, out, verbose=ctx.obj["verbose"])

        def count_nodes(node):
            return 1 + sum(count_nodes(c) for c in node.children)

        if not ctx.obj["quiet"]:
            click.echo(f"Done: {count_nodes(doc.root)} nodes.")

    @cli.command("tree-diff")
    @click.option("--target", default=".", help="Project root directory.")
    @click.pass_context
    def tree_diff(ctx, target):
        """Generate structure diff → tree-diff.json."""
        tgt = Path(target).resolve()
        out = tgt / HIPPO_DIR

        from .tools.tree_diff import run_tree_diff

        if not ctx.obj["quiet"]:
            click.echo("Computing tree diff ...")
        doc = run_tree_diff(out, verbose=ctx.obj["verbose"])
        if doc is None:
            click.echo("No baseline found, skipping diff.")
        elif not ctx.obj["quiet"]:
            click.echo(f"Done: {len(doc.changes)} changes.")

    return {
        "init": init,
        "sig-extract": sig_extract,
        "tree": tree,
        "tree-diff": tree_diff,
    }


__all__ = ["register_project_bootstrap_commands"]
