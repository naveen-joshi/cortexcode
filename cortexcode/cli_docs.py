from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn


def handle_docs_command(
    console: Console,
    path: Path,
    output: str | Path,
    open_browser: bool,
    require_index_path,
    print_docs_header,
    generate_all_docs,
    print_docs_complete,
) -> None:
    path, index_path = require_index_path(console, path)
    output = Path(output)

    print_docs_header(console, path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Generating documentation...", total=None)
        generate_all_docs(index_path, output)
        progress.update(task, completed=True)

    print_docs_complete(console, output)

    if open_browser:
        import webbrowser

        html_path = (output / "index.html").resolve()
        webbrowser.open(f"file:///{html_path}")
