import json
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def handle_dead_code_command(console: Console, path, detect_dead_code) -> None:
    path = Path(path).resolve()
    index_path = path / ".cortexcode" / "index.json"
    if not index_path.exists():
        console.print("[red]No index found. Run `cortexcode index` first.[/red]")
        return

    index = json.loads(index_path.read_text(encoding="utf-8"))
    dead = detect_dead_code(index)

    if not dead:
        console.print("[green]No dead code detected — all symbols are referenced.[/green]")
        return

    console.print(Panel.fit(
        f"[bold yellow]Potentially Unused Symbols[/bold yellow]\n"
        f"[dim]Found {len(dead)} symbols that are never called or imported[/dim]",
        border_style="yellow",
    ))

    table = Table(box=box.ROUNDED)
    table.add_column("Type", width=10)
    table.add_column("Name", style="cyan")
    table.add_column("File")
    table.add_column("Line", justify="right", width=5)

    for item in dead[:50]:
        table.add_row(item["type"], item["name"], item["file"], str(item["line"]))

    console.print(table)
    if len(dead) > 50:
        console.print(f"[dim]... and {len(dead) - 50} more[/dim]")
