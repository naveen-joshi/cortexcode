from pathlib import Path
from typing import Any, Callable


GetParser = Callable[[str], Any]
ExtractRegex = Callable[[str, str, str], list[dict[str, Any]]]
ExtractImportsRegex = Callable[[str, str], list[dict[str, Any]]]
ExtractSymbols = Callable[[str, Any, str], list[dict[str, Any]]]
ExtractImports = Callable[[str, Any, str], list[dict[str, Any]]]
ExtractExports = Callable[[str, Any, str], list[dict[str, Any]]]
ExtractApiRoutes = Callable[[str, Any, str], list[dict[str, Any]]]
ExtractEntities = Callable[[str, Any, str], list[dict[str, Any]]]


def index_file(
    file_path: Path,
    root: Path,
    regex_languages: dict[str, str],
    plugin_registry,
    get_parser: GetParser,
    extract_regex: ExtractRegex,
    extract_imports_regex: ExtractImportsRegex,
    extract_symbols: ExtractSymbols,
    extract_imports: ExtractImports,
    extract_exports: ExtractExports,
    extract_api_routes: ExtractApiRoutes,
    extract_entities: ExtractEntities,
) -> tuple[str, dict[str, Any], list[dict[str, Any]]] | None:
    ext = file_path.suffix.lower()

    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None

    rel_path = str(file_path.relative_to(root))

    plugin_symbols = plugin_registry.extract_symbols(content, ext, rel_path)
    if plugin_symbols is not None:
        plugin_imports = plugin_registry.extract_imports(content, ext) or []
        file_data = {
            "symbols": plugin_symbols,
            "imports": plugin_imports,
            "exports": [],
            "api_routes": [],
            "entities": [],
        }
        return rel_path, file_data, plugin_symbols

    if ext in regex_languages:
        symbols = extract_regex(content, ext, rel_path)
        imports = extract_imports_regex(content, ext)
        file_data = {
            "symbols": symbols,
            "imports": imports,
            "exports": [],
            "api_routes": [],
            "entities": [],
        }
        return rel_path, file_data, symbols

    parser = get_parser(ext)
    if not parser:
        return None

    try:
        tree = parser.parse(bytes(content, "utf8"))
    except Exception:
        return None

    symbols = extract_symbols(content, tree.root_node, ext)
    imports = extract_imports(content, tree.root_node, ext)
    exports = extract_exports(content, tree.root_node, ext)
    api_routes = extract_api_routes(content, tree.root_node, ext)
    entities = extract_entities(content, tree.root_node, ext)

    file_data = {
        "symbols": symbols,
        "imports": imports,
        "exports": exports,
        "api_routes": api_routes,
        "entities": entities,
    }
    return rel_path, file_data, symbols


def merge_indexed_file(
    rel_path: str,
    file_data: dict[str, Any],
    symbols: list[dict[str, Any]],
    file_symbols: dict[str, Any],
    all_symbols: list[dict[str, Any]],
    call_graph: dict[str, list[str]],
) -> None:
    file_symbols[rel_path] = file_data
    all_symbols.extend(symbols)

    for symbol in symbols:
        name = symbol.get("name")
        if not name:
            continue
        if name not in call_graph:
            call_graph[name] = []
        call_graph[name].extend(symbol.get("calls", []))
