from rich.console import Console
from rich.panel import Panel


def handle_explain_command(
    console: Console,
    symbol_name: str,
    path,
    provider,
    model,
    require_ai_doc_generator,
    require_index_path,
) -> None:
    AIDocGenerator = require_ai_doc_generator(console)
    _, index_path = require_index_path(console, path)
    generator = AIDocGenerator(provider=provider, model=model)
    result = generator.explain_symbol(index_path, symbol_name)

    console.print(Panel(
        result or "Could not generate explanation.",
        title=f"[bold]Explanation: {symbol_name}[/bold]",
        border_style="cyan",
    ))
