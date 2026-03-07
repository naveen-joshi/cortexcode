import json
from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table


def handle_search_command(
    console: Console,
    query: str,
    sym_type: str | None,
    file_filter: str | None,
    limit: int,
    index_path: Path,
) -> None:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    files = index.get("files", {})
    query_lower = query.lower()

    results = []
    for rel_path, file_data in files.items():
        if file_filter and file_filter.lower() not in rel_path.lower():
            continue

        symbols = file_data.get("symbols", []) if isinstance(file_data, dict) else file_data
        for sym in symbols:
            name = sym.get("name", "").lower()
            if query_lower in name:
                if sym_type and sym.get("type") != sym_type:
                    continue
                results.append({**sym, "file": rel_path})

    if not results:
        console.print(f"[yellow]No symbols matching '{query}'[/yellow]")
        return

    console.print(f"\n[bold]Found {len(results)} symbols matching '{query}':[/bold]\n")

    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("Type", style="dim", width=10)
    table.add_column("Name", style="cyan")
    table.add_column("File", style="dim")
    table.add_column("Line", justify="right")
    table.add_column("Calls", style="dim")

    for sym in results[:limit]:
        calls = sym.get("calls", [])
        calls_str = ", ".join(calls[:3]) + ("..." if len(calls) > 3 else "") if calls else ""
        table.add_row(
            sym.get("type", "?"),
            sym.get("name", "?"),
            sym.get("file", "?"),
            str(sym.get("line", "?")),
            calls_str,
        )

    console.print(table)

    if len(results) > limit:
        console.print(f"\n[dim]Showing {limit}/{len(results)} results. Use -n to see more.[/dim]")
