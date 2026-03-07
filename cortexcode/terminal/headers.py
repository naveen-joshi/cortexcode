from pathlib import Path

from rich.console import Console
from rich.panel import Panel


def print_index_header(console: Console, path: Path, incremental: bool) -> None:
    console.print(Panel.fit(
        f"[bold cyan]⚡ CortexCode Indexer[/bold cyan]\n"
        f"[dim]Scanning: {path}[/dim]" + (" (incremental)" if incremental else ""),
        border_style="cyan",
    ))


def print_docs_header(console: Console, path: Path) -> None:
    console.print(Panel.fit(
        f"[bold cyan]📄 Documentation Generator[/bold cyan]\n"
        f"[dim]Source: {path}[/dim]",
        border_style="cyan",
    ))


def print_diagrams_header(console: Console, path: Path) -> None:
    console.print(Panel.fit(
        f"[bold cyan]📊 Diagram Generator[/bold cyan]\n"
        f"[dim]Source: {path}[/dim]",
        border_style="cyan",
    ))


def print_ai_docs_header(console: Console, path: Path) -> None:
    console.print(Panel.fit(
        f"[bold cyan]🤖 AI Documentation Generator[/bold cyan]\n"
        f"[dim]Source: {path}[/dim]",
        border_style="cyan",
    ))
