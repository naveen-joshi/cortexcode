from pathlib import Path
from typing import Any, Callable

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


CalculateTokenSavings = Callable[..., dict[str, Any]]


def print_stats_header(console: Console) -> None:
    console.print(Panel.fit(
        "[bold cyan]CortexCode Stats[/bold cyan]",
        border_style="cyan",
    ))


def print_query_savings(
    console: Console,
    index_path: Path,
    call_graph: dict[str, Any],
    calculate_token_savings: CalculateTokenSavings,
) -> None:
    top_symbols = sorted(
        call_graph.items(),
        key=lambda x: len(x[1]) if isinstance(x[1], list) else 0,
        reverse=True,
    )[:3]

    if not top_symbols:
        return

    console.print("\n[bold]Per-Query Savings (top symbols):[/bold]\n")
    query_table = Table(box=box.SIMPLE, show_header=True)
    query_table.add_column("Query", style="cyan")
    query_table.add_column("Context Tokens", justify="right")
    query_table.add_column("vs Raw", justify="right", style="green")

    for name, _ in top_symbols:
        query_savings = calculate_token_savings(index_path, name, 5)
        query_table.add_row(
            name,
            f"{query_savings['context_tokens']:,}",
            f"{query_savings['savings_percent']}% saved",
        )

    console.print(query_table)
