"""Context Provider - Get relevant context for AI assistants."""

import json
import os
from pathlib import Path
from typing import Any

# Try to use tiktoken for accurate token counting
_tiktoken_encoder = None
try:
    import tiktoken
    _tiktoken_encoder = tiktoken.encoding_for_model("gpt-4")
except ImportError:
    pass


def estimate_tokens(text: str) -> int:
    """Estimate token count. Uses tiktoken if available, else ~4 chars/token heuristic."""
    if _tiktoken_encoder:
        return len(_tiktoken_encoder.encode(text))
    return max(1, len(text) // 4)


def estimate_file_tokens(file_path: Path) -> int:
    """Estimate tokens for an entire file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return estimate_tokens(content)
    except OSError:
        return 0


def calculate_token_savings(index_path: Path, query: str | None = None, num_results: int = 5) -> dict[str, Any]:
    """Calculate how many tokens CortexCode saves vs reading raw files.
    
    Returns:
        Dictionary with token counts for raw files vs indexed context
    """
    index = json.loads(index_path.read_text(encoding="utf-8"))
    files = index.get("files", {})
    project_root = Path(index.get("project_root", "."))
    
    # Calculate total project tokens (all source files)
    total_raw_tokens = 0
    file_count = 0
    for rel_path in files:
        full_path = project_root / rel_path
        if full_path.exists():
            total_raw_tokens += estimate_file_tokens(full_path)
            file_count += 1
    
    # Calculate index size in tokens
    index_text = index_path.read_text(encoding="utf-8")
    index_tokens = estimate_tokens(index_text)
    
    # Calculate context output tokens
    result = get_context(index_path, query, num_results)
    context_text = json.dumps(result, indent=2)
    context_tokens = estimate_tokens(context_text)
    
    savings_vs_raw = total_raw_tokens - context_tokens
    savings_pct = (savings_vs_raw / total_raw_tokens * 100) if total_raw_tokens > 0 else 0
    
    return {
        "raw_project_tokens": total_raw_tokens,
        "index_tokens": index_tokens,
        "context_tokens": context_tokens,
        "savings_tokens": savings_vs_raw,
        "savings_percent": round(savings_pct, 1),
        "file_count": file_count,
        "compression_ratio": round(total_raw_tokens / context_tokens, 1) if context_tokens > 0 else 0,
    }


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
        Dictionary with relevant symbols and their relationships
    """
    index = json.loads(index_path.read_text(encoding="utf-8"))
    
    files = index.get("files", {})
    call_graph = index.get("call_graph", {})
    file_deps = index.get("file_dependencies", {})
    project_root = index.get("project_root", "")
    
    if not query:
        return _get_all_symbols(files, call_graph, num_results)
    
    # Parse file-scoped query (e.g. "auth.ts:handleAuth")
    file_filter = None
    query_lower = query.lower()
    if ":" in query and not query.startswith(":"):
        parts = query.split(":", 1)
        file_filter = parts[0].lower()
        query_lower = parts[1].lower() if parts[1] else ""
    
    results = []
    
    for rel_path, file_data in files.items():
        # Apply file filter
        if file_filter and file_filter not in rel_path.lower():
            continue
        
        symbols = file_data.get("symbols", []) if isinstance(file_data, dict) else file_data
        imports = file_data.get("imports", []) if isinstance(file_data, dict) else []
        
        for sym in symbols:
            # If file-scoped with no symbol query, return all symbols in that file
            if file_filter and not query_lower:
                result = _build_symbol_result(sym, rel_path, call_graph)
                results.append(result)
                continue
            
            if _matches_query(sym, query_lower):
                result = _build_symbol_result(sym, rel_path, call_graph)
                results.append(result)
        
        if query_lower:
            for imp in imports:
                if query_lower in imp.get("module", "").lower():
                    results.append({
                        "name": imp.get("module"),
                        "type": "import",
                        "file": rel_path,
                        "imported": imp.get("imported", []),
                    })
    
    results = _rank_results(results, call_graph, query_lower)
    
    response = {
        "query": query,
        "symbols": results[:num_results],
        "total_found": len(results),
    }
    
    # Add file dependency info if file-scoped
    if file_filter:
        for rel_path in files:
            if file_filter in rel_path.lower():
                deps = file_deps.get(rel_path, [])
                if deps:
                    response["file_dependencies"] = deps
                break
    
    return response


def _build_symbol_result(sym: dict, rel_path: str, call_graph: dict) -> dict:
    """Build a context result dict for a symbol."""
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
    
    if sym.get("return_type"):
        result["return_type"] = sym["return_type"]
    
    if sym.get("methods"):
        result["methods"] = [m.get("name") for m in sym["methods"]]
    
    callers = [name for name, calls in call_graph.items() if sym.get("name") in calls]
    if callers:
        result["called_by"] = callers[:5]
    
    return result


def _get_all_symbols(files: dict, call_graph: dict, limit: int) -> dict[str, Any]:
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
    
    # Exact or substring match on name
    if query in name:
        return True
    
    # Fuzzy: all query chars appear in order in name
    if len(query) >= 3 and _fuzzy_match(query, name):
        return True
    
    # Match on calls
    calls = symbol.get("calls", [])
    for call in calls:
        if query in call.lower():
            return True
    
    # Match on class
    symbol_class = symbol.get("class")
    if symbol_class and query in symbol_class.lower():
        return True
    
    # Match on params
    params = symbol.get("params", [])
    for param in params:
        if query in param.lower():
            return True
    
    return False


def _fuzzy_match(query: str, target: str) -> bool:
    """Check if all characters in query appear in order in target."""
    qi = 0
    for ch in target:
        if qi < len(query) and ch == query[qi]:
            qi += 1
    return qi == len(query)


def _rank_results(results: list[dict], call_graph: dict, query: str) -> list[dict]:
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
        
        # Boost symbols that have callers (more connected = more important)
        if result.get("called_by"):
            score += len(result["called_by"]) * 5
        
        # Boost symbols that make calls (entry points)
        if result.get("calls"):
            score += min(len(result["calls"]), 5) * 2
        
        # Boost functions/classes over imports
        sym_type = result.get("type", "")
        if sym_type == "class":
            score += 15
        elif sym_type in ("function", "method"):
            score += 10
        elif sym_type == "interface":
            score += 5
        
        return score
    
    return sorted(results, key=relevance_score, reverse=True)


def format_context_for_ai(result: dict) -> str:
    """Format context as a text block suitable for pasting into AI chat."""
    lines = ["## Relevant Code Context\n"]
    
    for sym in result.get("symbols", []):
        lines.append(f"### {sym['name']} ({sym.get('type', 'unknown')})")
        lines.append(f"**File:** `{sym.get('file', 'unknown')}:{sym.get('line', '?')}`")
        
        if sym.get("params"):
            lines.append(f"**Params:** {', '.join(sym['params'])}")
        
        if sym.get("calls"):
            lines.append(f"**Calls:** {', '.join(sym['calls'])}")
        
        lines.append("")
    
    return "\n".join(lines)
