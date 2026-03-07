from pathlib import Path

from rich.console import Console


def handle_ai_docs_command(
    console: Console,
    path,
    output,
    provider,
    model,
    docs,
    require_ai_doc_generator,
    require_index_path,
    print_ai_docs_header,
    print_ai_docs_complete,
) -> None:
    AIDocGenerator = require_ai_doc_generator(console)

    path, index_path = require_index_path(console, path)
    output = Path(output)

    print_ai_docs_header(console, path)

    generator = AIDocGenerator(provider=provider, model=model)
    generator.generate_project_docs(index_path, output, list(docs))

    print_ai_docs_complete(console, output)
