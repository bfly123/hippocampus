from __future__ import annotations

import shutil
from pathlib import Path

import click


def register_hooks_commands(cli) -> click.Group:
    @cli.group("hooks")
    @click.pass_context
    def hooks_group(ctx):
        """Git hooks management."""
        pass

    @hooks_group.command("install")
    @click.option("--target", default=".", help="Project root directory.")
    @click.pass_context
    def hooks_install(ctx, target):
        """Install git hooks (pre-commit & post-commit)."""
        tgt = Path(target).resolve()
        git_hooks_dir = tgt / ".git" / "hooks"
        source_hooks_dir = tgt / "scripts" / "git-hooks"

        if not git_hooks_dir.exists():
            click.echo("Error: Not a git repository (no .git/hooks directory)")
            raise SystemExit(1)

        if not source_hooks_dir.exists():
            click.echo("Error: scripts/git-hooks directory not found")
            raise SystemExit(1)

        for hook_name in ("post-commit", "pre-commit"):
            source_hook = source_hooks_dir / hook_name
            target_hook = git_hooks_dir / hook_name

            if not source_hook.exists():
                click.echo(f"⚠️  Source hook {hook_name} not found, skipping")
                continue

            if target_hook.exists():
                if not ctx.obj["quiet"]:
                    click.echo(f"⚠️  {hook_name} hook already exists")
                    click.echo(f"   Backing up to {hook_name}.backup")
                shutil.copy2(target_hook, git_hooks_dir / f"{hook_name}.backup")

            shutil.copy2(source_hook, target_hook)
            target_hook.chmod(0o755)

        if not ctx.obj["quiet"]:
            click.echo("✅ Git hooks installed successfully")
            click.echo("   pre-commit:  Architecture review (blocks violations)")
            click.echo("   post-commit: Auto-refresh hippo index")

    @hooks_group.command("uninstall")
    @click.option("--target", default=".", help="Project root directory.")
    @click.pass_context
    def hooks_uninstall(ctx, target):
        """Uninstall git hooks."""
        tgt = Path(target).resolve()
        git_hooks_dir = tgt / ".git" / "hooks"

        for hook_name in ("post-commit", "pre-commit"):
            target_hook = git_hooks_dir / hook_name
            backup_hook = git_hooks_dir / f"{hook_name}.backup"

            if not target_hook.exists():
                continue

            content = target_hook.read_text()
            if "Hippocampus" not in content:
                click.echo(
                    f"⚠️  {hook_name} exists but is not a Hippocampus hook, skipping"
                )
                continue

            target_hook.unlink()
            if backup_hook.exists():
                shutil.copy2(backup_hook, target_hook)
                backup_hook.unlink()
                if not ctx.obj["quiet"]:
                    click.echo(f"✅ {hook_name} removed, backup restored")
            elif not ctx.obj["quiet"]:
                click.echo(f"✅ {hook_name} removed")

    @hooks_group.command("status")
    @click.option("--target", default=".", help="Project root directory.")
    @click.pass_context
    def hooks_status(ctx, target):
        """Check git hooks installation status."""
        tgt = Path(target).resolve()
        git_hooks_dir = tgt / ".git" / "hooks"

        if not git_hooks_dir.exists():
            click.echo("❌ Not a git repository")
            return

        for hook_name in ("post-commit", "pre-commit"):
            target_hook = git_hooks_dir / hook_name
            if not target_hook.exists():
                click.echo(f"❌ {hook_name}: Not installed")
                continue
            content = target_hook.read_text()
            if "Hippocampus" in content:
                click.echo(f"✅ {hook_name}: Installed")
            else:
                click.echo(f"⚠️  {hook_name}: Exists but not a Hippocampus hook")

    return hooks_group
