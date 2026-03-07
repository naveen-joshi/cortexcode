import json
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def handle_diff_command(console: Console, ref: str, output_format: str, index_path: Path, get_diff_context) -> None:
    result = get_diff_context(index_path, ref)

    if output_format == "json":
        console.print(json.dumps(result, indent=2))
        return

    if result["changed_files"] == 0:
        console.print("[green]No changes detected.[/green]")
        return

    console.print(Panel.fit(
        f"[bold cyan]Git Diff Context[/bold cyan]\n"
        f"[dim]Comparing against: {ref}[/dim]",
        border_style="cyan",
    ))

    console.print(f"\n[bold]{result['changed_files']}[/bold] files changed\n")

    changed = result.get("changed_symbols", [])
    if changed:
        table = Table(title="Changed Symbols", box=box.SIMPLE, show_header=True)
        table.add_column("", width=3)
        table.add_column("Type", style="dim", width=10)
        table.add_column("Name", style="cyan")
        table.add_column("File", style="dim")
        table.add_column("Line", justify="right")

        for sym in changed:
            marker = "[red]*[/red]" if sym.get("changed") else "[dim]~[/dim]"
            table.add_row(
                marker,
                sym.get("type", "?"),
                sym.get("name", "?"),
                sym.get("file", "?"),
                str(sym.get("line", "?")),
            )

        console.print(table)
        console.print("[dim]  [red]*[/red] = in changed lines  [dim]~[/dim] = in changed file[/dim]\n")

    affected = result.get("affected_symbols", [])
    if affected:
        console.print("[bold yellow]Potentially affected symbols:[/bold yellow]\n")
        for sym in affected:
            calls_changed = ", ".join(sym.get("calls_changed", []))
            console.print(f"  [yellow]{sym['name']}[/yellow] ({sym.get('type', '?')}) in {sym.get('file', '?')}")
            console.print(f"    [dim]calls changed: {calls_changed}[/dim]")
