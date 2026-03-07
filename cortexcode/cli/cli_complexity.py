import json
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def handle_complexity_command(console: Console, path, top: int, min_score: int, compute_complexity) -> None:
    path = Path(path).resolve()
    index_path = path / ".cortexcode" / "index.json"
    if not index_path.exists():
        console.print("[red]No index found. Run `cortexcode index` first.[/red]")
        return

    index = json.loads(index_path.read_text(encoding="utf-8"))
    results = compute_complexity(index, project_root=str(path))

    if min_score > 0:
        results = [result for result in results if result.get("score", 0) >= min_score]

    if not results:
        console.print("[green]No complex functions found.[/green]")
        return

    ratings = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for result in results:
        ratings[result.get("rating", "low")] += 1

    console.print(Panel.fit(
        f"[bold cyan]Complexity Analysis[/bold cyan]\n"
        f"[green]Low: {ratings['low']}[/green]  [yellow]Medium: {ratings['medium']}[/yellow]  "
        f"[red]High: {ratings['high']}[/red]  [bold red]Critical: {ratings['critical']}[/bold red]",
        border_style="cyan",
    ))

    table = Table(title=f"Top {top} Most Complex Functions", box=box.ROUNDED)
    table.add_column("Score", justify="right", width=6)
    table.add_column("Rating", width=8)
    table.add_column("Name", style="cyan")
    table.add_column("Lines", justify="right", width=6)
    table.add_column("CC", justify="right", width=4)
    table.add_column("Nest", justify="right", width=4)
    table.add_column("Params", justify="right", width=6)
    table.add_column("File")

    for result in results[:top]:
        rating = result.get("rating", "low")
        color = {"low": "green", "medium": "yellow", "high": "red", "critical": "bold red"}[rating]
        table.add_row(
            str(result.get("score", 0)),
            f"[{color}]{rating}[/{color}]",
            result["name"],
            str(result.get("lines", "?")),
            str(result.get("cyclomatic", "?")),
            str(result.get("max_nesting", "?")),
            str(result.get("params_count", 0)),
            result["file"],
        )

    console.print(table)
