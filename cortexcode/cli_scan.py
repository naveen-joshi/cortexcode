from pathlib import Path

from rich.console import Console
from rich.panel import Panel


def handle_scan_command(console: Console, path, scan_dependencies) -> None:
    path = Path(path).resolve()

    console.print(Panel.fit(
        f"[bold cyan]Dependency Scanner[/bold cyan]\n"
        f"[dim]Scanning: {path}[/dim]",
        border_style="cyan",
    ))

    result = scan_dependencies(path)

    if not result["scanned_files"]:
        console.print("[yellow]No dependency files found.[/yellow]")
        return

    console.print(f"\n[bold]Scanned:[/bold] {', '.join(result['scanned_files'])}")
    console.print(f"[bold]Dependencies found:[/bold] {result['total_dependencies']}")

    warnings = result.get("warnings", [])
    if warnings:
        console.print(f"\n[bold yellow]Warnings ({len(warnings)}):[/bold yellow]\n")
        for warning in warnings:
            severity_color = {"high": "red", "medium": "yellow", "low": "dim"}.get(warning["severity"], "white")
            console.print(
                f"  [{severity_color}][{warning['severity'].upper()}][/{severity_color}] {warning['package']}: {warning['message']}"
            )
    else:
        console.print("\n[green]No warnings found.[/green]")
