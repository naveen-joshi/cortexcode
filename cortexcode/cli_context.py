import json
import sys
from pathlib import Path

from rich.console import Console


def handle_context_command(
    console: Console,
    query,
    num_results: int,
    output_format: str,
    tokens: bool,
    get_context,
    calculate_token_savings,
    print_context,
    print_token_savings,
) -> None:
    index_path = Path('.cortexcode/index.json')

    if not index_path.exists():
        console.print("[bold red]Error:[/bold red] No index found. Run 'cortexcode index' first.")
        sys.exit(1)

    result = get_context(index_path, query, num_results)

    if output_format == 'json':
        console.print(json.dumps(result, indent=2))
    else:
        print_context(console, result)

    if tokens:
        savings = calculate_token_savings(index_path, query, num_results)
        print_token_savings(console, savings)
