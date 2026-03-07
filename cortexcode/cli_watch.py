from pathlib import Path

from rich.console import Console


def handle_watch_command(console: Console, path, verbose: bool, start_watcher) -> None:
    path = Path(path).resolve()
    console.print(f"[bold blue]Watching:[/bold blue] {path}")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    start_watcher(path, verbose=verbose)
