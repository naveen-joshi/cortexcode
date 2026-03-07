from rich.console import Console


def handle_mcp_command(console: Console, run_stdio_server) -> None:
    console.print("[dim]CortexCode MCP server started (stdin/stdout)[/dim]")
    run_stdio_server()


def handle_lsp_command(run_lsp_server) -> None:
    run_lsp_server()
