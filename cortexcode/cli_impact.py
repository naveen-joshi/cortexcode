import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel


def handle_impact_command(console: Console, symbol: str, path, analyze_change_impact) -> None:
    path = Path(path).resolve()
    index_path = path / ".cortexcode" / "index.json"
    if not index_path.exists():
        console.print("[red]No index found. Run `cortexcode index` first.[/red]")
        return

    index = json.loads(index_path.read_text(encoding="utf-8"))
    result = analyze_change_impact(index, symbol)
    risk_color = {"low": "green", "medium": "yellow", "high": "red"}[result["risk"]]

    console.print(Panel.fit(
        f"[bold cyan]Change Impact Analysis[/bold cyan]\n"
        f"Symbol: [bold]{symbol}[/bold]\n"
        f"Risk: [{risk_color}]{result['risk'].upper()}[/{risk_color}]  |  "
        f"Total impact: {result['total_impact']} symbols",
        border_style="cyan",
    ))

    if result["direct_callers"]:
        console.print(f"\n[bold]Direct callers ({len(result['direct_callers'])}):[/bold]")
        for caller in result["direct_callers"]:
            console.print(f"  [cyan]{caller}[/cyan]")

    if result["indirect_callers"]:
        console.print(f"\n[bold]Indirect callers ({len(result['indirect_callers'])}):[/bold]")
        for caller in result["indirect_callers"]:
            console.print(f"  [dim]{caller}[/dim]")

    if result["affected_files"]:
        console.print(f"\n[bold]Affected files ({len(result['affected_files'])}):[/bold]")
        for file_path in result["affected_files"]:
            console.print(f"  {file_path}")

    if result["affected_tests"]:
        console.print(f"\n[bold yellow]Tests to update ({len(result['affected_tests'])}):[/bold yellow]")
        for file_path in result["affected_tests"]:
            console.print(f"  {file_path}")

    if result["importing_files"]:
        console.print(f"\n[bold]Files importing affected modules ({len(result['importing_files'])}):[/bold]")
        for file_path in result["importing_files"]:
            console.print(f"  [dim]{file_path}[/dim]")
