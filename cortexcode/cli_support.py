import sys
from pathlib import Path

from rich.console import Console


ERROR_MESSAGE = "[bold red]Error:[/bold red] No index found. Run 'cortexcode index' first."


def resolve_project_path(path: str | Path) -> Path:
    return Path(path).resolve()


def require_index_path(console: Console, path: str | Path) -> tuple[Path, Path]:
    project_path = resolve_project_path(path)
    index_path = project_path / ".cortexcode" / "index.json"
    if not index_path.exists():
        console.print(ERROR_MESSAGE)
        sys.exit(1)
    return project_path, index_path


def require_ai_doc_generator(console: Console):
    try:
        from cortexcode.ai_docs import AIDocGenerator
    except ImportError as exc:
        console.print(f"[bold red]Error:[/bold red] AI docs module not available: {exc}")
        console.print("[dim]Install with: pip install cortexcode[ai] or pip install openai anthropic[/dim]")
        sys.exit(1)
    return AIDocGenerator
