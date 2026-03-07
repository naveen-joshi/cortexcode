from typing import Any, Callable


Extractor = Callable[[str, Any, list[dict[str, Any]], str | None], None]


def extract_symbols_by_extension(
    source: str,
    node: Any,
    ext: str,
    extract_python: Extractor,
    extract_javascript: Extractor,
    extract_typescript: Extractor,
    extract_go: Extractor,
    extract_rust: Extractor,
    extract_java: Extractor,
    extract_csharp: Extractor,
    extract_kotlin: Extractor,
    extract_swift: Extractor,
) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []

    if ext == ".py":
        extract_python(source, node, symbols, None)
    elif ext in (".js", ".jsx"):
        extract_javascript(source, node, symbols, None)
    elif ext in (".ts", ".tsx"):
        extract_typescript(source, node, symbols, None)
    elif ext == ".go":
        extract_go(source, node, symbols, None)
    elif ext == ".rs":
        extract_rust(source, node, symbols, None)
    elif ext == ".java":
        extract_java(source, node, symbols, None)
    elif ext == ".cs":
        extract_csharp(source, node, symbols, None)
    elif ext in (".kt", ".kts"):
        extract_kotlin(source, node, symbols, None)
    elif ext == ".swift":
        extract_swift(source, node, symbols, None)

    return symbols
