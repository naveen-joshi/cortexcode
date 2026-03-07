from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def print_context(console: Console, result: dict[str, Any]) -> None:
    if not result.get("symbols"):
        console.print("[yellow]No matching symbols found.[/yellow]")
        return

    console.print("\n[bold]Relevant Symbols:[/bold]\n")

    for sym in result["symbols"]:
        console.print(f"  [cyan]{sym['name']}[/cyan] ({sym.get('type', 'unknown')})")
        console.print(f"    File: {sym.get('file', 'unknown')}:{sym.get('line', '?')}")
        if sym.get("params"):
            console.print(f"    Params: {', '.join(sym['params'])}")
        if sym.get("calls"):
            console.print(f"    Calls: {', '.join(sym['calls'])}")
        if sym.get("called_by"):
            console.print(f"    Called by: {', '.join(sym['called_by'])}")
        console.print()


def print_token_savings(console: Console, savings: dict[str, Any]) -> None:
    console.print()
    table = Table(
        title="[bold]Token Savings Analysis[/bold]",
        box=box.ROUNDED,
        show_header=False,
    )
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")

    raw = savings["raw_project_tokens"]
    ctx = savings["context_tokens"]
    idx = savings["index_tokens"]

    table.add_row("Source files", f"{savings['file_count']} files")
    table.add_row("Raw project tokens", f"[red]{raw:,}[/red]")
    table.add_row("Full index tokens", f"[yellow]{idx:,}[/yellow]")
    table.add_row("Context query tokens", f"[green]{ctx:,}[/green]")
    table.add_row("", "")
    table.add_row("Tokens saved", f"[bold green]{savings['savings_tokens']:,}[/bold green]")
    table.add_row("Savings", f"[bold green]{savings['savings_percent']}%[/bold green]")
    table.add_row("Compression ratio", f"[bold]{savings['compression_ratio']}x[/bold]")

    console.print(Panel(table, border_style="green"))

    cost_raw = raw / 1_000_000 * 30
    cost_ctx = ctx / 1_000_000 * 30
    cost_saved = cost_raw - cost_ctx

    if cost_saved > 0.001:
        console.print(
            f"  [dim]Estimated cost per query (GPT-4 rates):[/dim]\n"
            f"  [red]Without CortexCode:[/red] ${cost_raw:.4f}\n"
            f"  [green]With CortexCode:[/green]    ${cost_ctx:.4f}\n"
            f"  [bold green]Saved per query:[/bold green]     ${cost_saved:.4f}\n"
        )
