from pathlib import Path
from typing import Sequence

from rich.console import Console
from rich.panel import Panel


def print_docs_complete(console: Console, output: Path) -> None:
    console.print()
    console.print(Panel(
        f"[bold green]✓[/bold green] Documentation generated successfully!\n\n"
        f"[cyan]Output:[/cyan] {output}\n"
        f"[cyan]HTML:[/cyan] {output}/index.html\n"
        f"[cyan]Reports:[/cyan] README.md, API.md, FLOWS.md, TECH.md, INSIGHTS.md\n\n"
        f"[dim]Open index.html in a browser to view interactive documentation.[/dim]",
        title="[bold]Documentation Complete[/bold]",
        border_style="green",
    ))


def print_diagrams_complete(console: Console, output: Path, generated_files: Sequence[str]) -> None:
    console.print()
    console.print(Panel(
        f"[bold green]✓[/bold green] Diagrams generated!\n\n"
        f"[cyan]Output:[/cyan] {output}\n"
        f"[cyan]Files:[/cyan] {', '.join(generated_files)}",
        title="[bold]Diagrams Complete[/bold]",
        border_style="green",
    ))


def print_ai_docs_complete(console: Console, output: Path) -> None:
    console.print()
    console.print(Panel(
        f"[bold green]✓[/bold green] AI Documentation generated!\n\n"
        f"[cyan]Output:[/cyan] {output}",
        title="[bold]AI Docs Complete[/bold]",
        border_style="green",
    ))
