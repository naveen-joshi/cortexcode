import json
from pathlib import Path
from typing import Any


def get_context(index_path: Path, query: str | None = None, num_results: int = 5) -> dict[str, Any]:
    """Get relevant context from the index for AI assistants.

    Args:
        index_path: Path to the index.json file
        query: Optional search query. Supports:
            - symbol name: "handleAuth"
            - file-scoped: "auth.ts:handleAuth"
            - fuzzy: "hndlAuth"
        num_results: Number of results to return

    Returns:
        Dictionary with relevant symbols and their code snippets
    """
    index = json.loads(index_path.read_text(encoding="utf-8"))

    files = index.get("files", {})
    call_graph = index.get("call_graph", {})
    file_deps = index.get("file_dependencies", {})
    source_code = index.get("source_code", {})

    if not query:
        return _get_all_symbols(files, call_graph, source_code, num_results)

    file_filter = None
    query_lower = query.lower()
    if ":" in query and not query.startswith(":"):
        parts = query.split(":", 1)
        file_filter = parts[0].lower()
        query_lower = parts[1].lower() if parts[1] else ""

    results = []

    for rel_path, file_data in files.items():
        if file_filter and file_filter not in rel_path.lower():
            continue

        symbols = file_data.get("symbols", []) if isinstance(file_data, dict) else file_data
        imports = file_data.get("imports", []) if isinstance(file_data, dict) else []

        for sym in symbols:
            if file_filter and not query_lower:
                results.append(_build_symbol_result(sym, rel_path, call_graph, source_code))
                continue

            if _matches_query(sym, query_lower):
                results.append(_build_symbol_result(sym, rel_path, call_graph, source_code))

        if query_lower:
            for imp in imports:
                if query_lower in imp.get("module", "").lower():
                    results.append({
                        "name": imp.get("module"),
                        "type": "import",
                        "file": rel_path,
                        "imported": imp.get("imported", []),
                    })

    results = _rank_results(results, query_lower)

    response = {
        "query": query,
        "symbols": results[:num_results],
        "total_found": len(results),
    }

    if file_filter:
        for rel_path in files:
            if file_filter in rel_path.lower():
                deps = file_deps.get(rel_path, [])
                if deps:
                    response["file_dependencies"] = deps
                break

    return response


def _build_symbol_result(sym: dict, rel_path: str, call_graph: dict, source_code: dict) -> dict:
    """Build a context result dict for a symbol with actual code."""
    result = {
        "name": sym.get("name"),
        "type": sym.get("type"),
        "file": rel_path,
        "line": sym.get("line"),
        "params": sym.get("params", []),
        "calls": sym.get("calls", []),
        "class": sym.get("class"),
        "framework": sym.get("framework"),
    }

    # Add actual code snippet from source_code - look up by symbol name + type
    code = _get_symbol_code(sym.get("name"), sym.get("type"), rel_path, source_code)
    if code:
        result["code"] = code

    if sym.get("return_type"):
        result["return_type"] = sym["return_type"]

    if sym.get("methods"):
        result["methods"] = [method.get("name") for method in sym["methods"]]

    callers = [name for name, calls in call_graph.items() if sym.get("name") in calls]
    if callers:
        result["called_by"] = callers[:5]

    return result


def _get_symbol_code(sym_name: str, sym_type: str, rel_path: str, source_code: dict) -> str | None:
    """Get the actual code snippet for a symbol from source_code storage."""
    if not source_code or not sym_name:
        return None

    # Try to find by symbol name + type key first
    key = f"{sym_name}:{sym_type}"
    if key in source_code:
        file_data = source_code[key].get(rel_path)
        if file_data:
            return file_data.get("body")
    
    # Fallback: search through all keys for this symbol name
    for code_key, files in source_code.items():
        if code_key.startswith(f"{sym_name}:"):
            file_data = files.get(rel_path)
            if file_data:
                return file_data.get("body")
    
    return None


def _get_all_symbols(files: dict, call_graph: dict, source_code: dict, limit: int) -> dict[str, Any]:
    """Get all symbols, limited."""
    all_symbols = []

    for rel_path, file_data in files.items():
        symbols = file_data.get("symbols", []) if isinstance(file_data, dict) else file_data
        for sym in symbols:
            all_symbols.append({
                "name": sym.get("name"),
                "type": sym.get("type"),
                "file": rel_path,
                "line": sym.get("line"),
                "params": sym.get("params", []),
                "calls": sym.get("calls", []),
            })

    return {
        "symbols": all_symbols[:limit],
        "total_found": len(all_symbols),
    }


def _matches_query(symbol: dict, query: str) -> bool:
    """Check if symbol matches the query (supports fuzzy and file-scoped)."""
    name = symbol.get("name", "").lower()

    if query in name:
        return True

    if len(query) >= 3 and _fuzzy_match(query, name):
        return True

    calls = symbol.get("calls", [])
    for call in calls:
        if query in call.lower():
            return True

    symbol_class = symbol.get("class")
    if symbol_class and query in symbol_class.lower():
        return True

    params = symbol.get("params", [])
    for param in params:
        if query in param.lower():
            return True

    return False


def _fuzzy_match(query: str, target: str) -> bool:
    """Check if all characters in query appear in order in target."""
    query_index = 0
    for character in target:
        if query_index < len(query) and character == query[query_index]:
            query_index += 1
    return query_index == len(query)


def _rank_results(results: list[dict], query: str) -> list[dict]:
    """Rank results by relevance."""
    def relevance_score(result: dict) -> int:
        score = 0
        name = result.get("name", "").lower()

        if name == query:
            score += 100
        elif name.startswith(query):
            score += 50
        elif query in name:
            score += 10

        if result.get("called_by"):
            score += len(result["called_by"]) * 5

        if result.get("calls"):
            score += min(len(result["calls"]), 5) * 2

        sym_type = result.get("type", "")
        if sym_type == "class":
            score += 15
        elif sym_type in ("function", "method"):
            score += 10
        elif sym_type == "interface":
            score += 5

        return score

    return sorted(results, key=relevance_score, reverse=True)
