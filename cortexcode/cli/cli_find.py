from rich import box
from rich.console import Console
from rich.table import Table


def handle_semantic_find_command(
    console: Console,
    query: str,
    limit: int,
    require_index_path,
    semantic_search,
) -> None:
    _, index_path = require_index_path(console, ".")
    result = semantic_search(index_path, query, limit)
    results = result.get("results", [])

    if not results:
        console.print(f"[yellow]No results for '{query}'[/yellow]")
        return

    console.print(f"\n[bold]Semantic search: \"{query}\"[/bold]  ({len(results)} results from {result['total_symbols']} symbols)\n")

    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("Score", justify="right", width=6)
    table.add_column("Type", style="dim", width=10)
    table.add_column("Name", style="cyan")
    table.add_column("File", style="dim")
    table.add_column("Line", justify="right", width=5)

    for item in results:
        score_color = "green" if item["score"] > 0.3 else "yellow" if item["score"] > 0.1 else "dim"
        table.add_row(
            f"[{score_color}]{item['score']:.2f}[/{score_color}]",
            item.get("type", "?"),
            item.get("name", "?"),
            item.get("file", "?"),
            str(item.get("line", "?")),
        )

    console.print(table)
