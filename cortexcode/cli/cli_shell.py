"""CLI shell helpers for help formatting, legacy aliases, and completion."""

from __future__ import annotations

import functools
import os
from pathlib import Path

import click
from rich.console import Console


class SectionedHelpGroup(click.Group):
    """A Click group that renders commands in logical sections."""

    command_sections: dict[str, list[str]] = {}

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        commands: dict[str, click.Command] = {}
        for name in self.list_commands(ctx):
            cmd = self.get_command(ctx, name)
            if cmd is None or cmd.hidden:
                continue
            commands[name] = cmd

        if not commands:
            return

        seen: set[str] = set()
        for section_name, names in self.command_sections.items():
            rows: list[tuple[str, str]] = []
            for name in names:
                cmd = commands.get(name)
                if cmd is None:
                    continue
                rows.append((name, cmd.get_short_help_str()))
                seen.add(name)
            if rows:
                with formatter.section(section_name):
                    formatter.write_dl(rows)

        remaining = [(name, cmd.get_short_help_str()) for name, cmd in commands.items() if name not in seen]
        if remaining:
            with formatter.section("Other"):
                formatter.write_dl(sorted(remaining))


def install_legacy_alias_tips(
    group: click.Group,
    *,
    console: Console,
    aliases: dict[str, str],
    hidden: bool = True,
) -> None:
    """Hide legacy aliases from help and show a tip when they are used."""
    for old_name, new_name in aliases.items():
        cmd = group.commands.get(old_name)
        if cmd is None:
            continue
        if hidden:
            cmd.hidden = True
        if getattr(cmd, "_cortexcode_legacy_wrapped", False):
            continue

        original_callback = cmd.callback
        if original_callback is None:
            continue

        @functools.wraps(original_callback)
        def wrapped(*args, __old_name=old_name, __new_name=new_name, __callback=original_callback, **kwargs):
            console.print(
                f"[dim]Tip: `cortexcode {__old_name}` is a legacy shortcut. Prefer `cortexcode {__new_name}`.[/dim]"
            )
            return __callback(*args, **kwargs)

        cmd.callback = wrapped
        cmd._cortexcode_legacy_wrapped = True


def build_completion_script(shell: str, prog: str) -> str:
    env_name = f"_{prog.replace('-', '_').upper()}_COMPLETE"
    if shell == "bash":
        return f'eval "$({env_name}=bash_source {prog})"'
    if shell == "zsh":
        return f'eval "$({env_name}=zsh_source {prog})"'
    if shell == "fish":
        return f"{env_name}=fish_source {prog} | source"
    if shell == "powershell":
        return f"{env_name}=powershell_source {prog} | Out-String | Invoke-Expression"
    raise click.ClickException(f"Unsupported shell: {shell}")


def default_completion_path(shell: str) -> Path:
    home = Path.home()
    if shell == "bash":
        return home / ".bashrc"
    if shell == "zsh":
        return home / ".zshrc"
    if shell == "fish":
        return home / ".config" / "fish" / "config.fish"
    if shell == "powershell":
        return home / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
    raise click.ClickException(f"Unsupported shell: {shell}")


def detect_shell() -> str:
    if os.name == "nt":
        return "powershell"
    shell = os.environ.get("SHELL", "")
    if shell.endswith("zsh"):
        return "zsh"
    if shell.endswith("fish"):
        return "fish"
    return "bash"


def handle_completion_show(console: Console, shell: str | None, prog: str) -> None:
    resolved_shell = shell or detect_shell()
    script = build_completion_script(resolved_shell, prog)
    console.print(f"[bold]Shell completion for {prog} ({resolved_shell})[/bold]\n")
    console.print(script)


def handle_completion_install(console: Console, shell: str | None, prog: str, path: str | None) -> None:
    resolved_shell = shell or detect_shell()
    target = Path(path) if path else default_completion_path(resolved_shell)
    line = build_completion_script(resolved_shell, prog)
    target.parent.mkdir(parents=True, exist_ok=True)

    existing = target.read_text(encoding="utf-8", errors="ignore") if target.exists() else ""
    if line in existing:
        console.print(f"[yellow]Completion already installed in[/yellow] {target}")
        return

    prefix = "\n" if existing and not existing.endswith("\n") else ""
    target.write_text(existing + prefix + line + "\n", encoding="utf-8")
    console.print(f"[green]✓[/green] Installed {prog} completion to {target}")
    console.print("[dim]Restart your shell or reload the profile to activate completion.[/dim]")


def handle_completion_paths(console: Console) -> None:
    console.print("[bold]Default completion profile targets[/bold]\n")
    for shell in ["powershell", "bash", "zsh", "fish"]:
        console.print(f"[cyan]{shell}[/cyan]: {default_completion_path(shell)}")
