from pathlib import Path

from rich.console import Console


def handle_diagrams_command(
    console: Console,
    path,
    output,
    diagram_type,
    require_index_path,
    print_diagrams_header,
    save_diagrams,
    diagram_types: list[str],
    print_diagrams_complete,
) -> None:
    path, index_path = require_index_path(console, path)
    output = Path(output)

    print_diagrams_header(console, path)

    save_diagrams(index_path, output, diagram_type=diagram_type)
    generated_files = [f"{diagram_type}.mmd"] if diagram_type else [f"{name}.mmd" for name in diagram_types]
    generated_files.insert(0, "DIAGRAMS.md")

    print_diagrams_complete(console, output, generated_files)
