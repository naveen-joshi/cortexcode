import json

from rich.console import Console


def handle_stats_command(
    console: Console,
    require_index_path,
    print_stats_header,
    calculate_token_savings,
    print_token_savings,
    print_query_savings,
) -> None:
    _, index_path = require_index_path(console, ".")
    print_stats_header(console)
    savings = calculate_token_savings(index_path)
    print_token_savings(console, savings)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    call_graph = index.get("call_graph", {})
    print_query_savings(console, index_path, call_graph, calculate_token_savings)
