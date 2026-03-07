import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel


def handle_dashboard_command(console: Console, path, port: int, indexer_module, DashboardServer) -> None:
    path = Path(path).resolve()
    index_path = path / ".cortexcode" / "index.json"

    if not index_path.exists():
        console.print("[yellow]No index found. Indexing first...[/yellow]")
        indexer = indexer_module.CodeIndexer()
        index = indexer.index_directory(path)
        output_dir = path / ".cortexcode"
        output_dir.mkdir(exist_ok=True)
        index_path.write_text(json.dumps(index, indent=2, default=str), encoding="utf-8")

    docs_dir = path / ".cortexcode" / "docs"
    console.print(Panel.fit(
        f"[bold cyan]CortexCode Live Dashboard[/bold cyan]\n"
        f"[dim]Serving: {docs_dir}[/dim]\n"
        f"[bold green]http://localhost:{port}[/bold green]\n"
        f"[dim]Auto-refreshes when index changes[/dim]",
        border_style="cyan",
    ))
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    server = DashboardServer(path, port)
    server.start(open_browser=True)
