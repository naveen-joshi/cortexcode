"""Flow tracing - trace code execution paths through call graph."""

import json
from collections import deque
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax


def trace_call_chain(call_graph: dict, start_symbol: str, max_depth: int = 5) -> dict:
    """Trace all paths from a starting symbol through the call graph."""
    visited = set()
    paths = []
    
    def dfs(symbol: str, path: list, depth: int):
        if depth > max_depth or symbol in visited:
            return
        
        visited.add(symbol)
        path = path + [symbol]
        
        callees = call_graph.get(symbol, [])
        if not callees:
            paths.append(path)
        else:
            for callee in callees:
                dfs(callee, path, depth + 1)
        
        visited.remove(symbol)
    
    dfs(start_symbol, [], 0)
    return paths


def find_entry_points(call_graph: dict) -> list[str]:
    """Find symbols that are called but don't call others (terminal nodes)."""
    all_callers = set(call_graph.keys())
    all_callees = set()
    for callees in call_graph.values():
        all_callees.update(callees)
    
    # Entry points are symbols that are called but don't call others
    entry_points = all_callees - all_callers
    return sorted(entry_points)


def find_symbols_matching(call_graph: dict, query: str) -> list[dict]:
    """Find symbols that match a query (name or pattern)."""
    query_lower = query.lower()
    matches = []
    
    for symbol in call_graph.keys():
        if query_lower in symbol.lower():
            matches.append({
                "symbol": symbol,
                "calls": call_graph.get(symbol, []),
            })
    
    return matches


def trace_flow_from_multiple_starts(call_graph: dict, queries: list[str], max_depth: int = 5) -> dict:
    """Trace flow from multiple starting points (e.g., multiple auth-related functions)."""
    all_paths = []
    matched_symbols = []
    
    for query in queries:
        matches = find_symbols_matching(call_graph, query)
        for match in matches:
            if match["symbol"] not in matched_symbols:
                matched_symbols.append(match["symbol"])
                paths = trace_call_chain(call_graph, match["symbol"], max_depth)
                all_paths.extend(paths)
    
    return {
        "matched_symbols": matched_symbols,
        "paths": all_paths[:50],  # Limit to 50 paths
        "total_paths": len(all_paths),
    }


def get_symbol_context(index_data: dict, symbol_name: str) -> dict:
    """Get detailed context for a symbol including file, line, and code."""
    files = index_data.get("files", {})
    
    for file_path, file_data in files.items():
        symbols = file_data.get("symbols", []) if isinstance(file_data, dict) else file_data
        for sym in symbols:
            if sym.get("name") == symbol_name:
                return {
                    "file": file_path,
                    "line": sym.get("line", 0),
                    "type": sym.get("type", "unknown"),
                    "params": sym.get("params", []),
                    "class": sym.get("class", ""),
                }
    
    return {}


def handle_trace_command(console: Console, query: str, path: str, depth: int, context_lines: int) -> None:
    """CLI handler for trace command."""
    from cortexcode.cli import require_index_path
    
    path, index_path = require_index_path(console, path)
    
    with open(index_path) as f:
        index_data = json.load(f)
    
    call_graph = index_data.get("call_graph", {})
    
    if not call_graph:
        console.print("[yellow]No call graph found in index[/yellow]")
        return
    
    # Find matching symbols
    matches = find_symbols_matching(call_graph, query)
    
    if not matches:
        console.print(f"[yellow]No symbols found matching '{query}'[/yellow]")
        return
    
    console.print(f"\n[bold cyan]Found {len(matches)} symbols matching '{query}':[/bold cyan]\n")
    
    for match in matches[:10]:
        symbol = match["symbol"]
        callees = match["calls"]
        
        # Get symbol context
        sym_context = get_symbol_context(index_data, symbol)
        
        console.print(f"[green]• {symbol}[/green]")
        console.print(f"  File: {sym_context.get('file', 'unknown')}:{sym_context.get('line', 0)}")
        console.print(f"  Type: {sym_context.get('type', 'unknown')}")
        
        if callees:
            console.print(f"  Calls: {', '.join(callees[:5])}")
            if len(callees) > 5:
                console.print(f"         ... and {len(callees) - 5} more")
        else:
            console.print(f"  Calls: (none)")
        console.print()
    
    # Trace flow from matches
    if matches:
        console.print("[bold cyan]Tracing call chains:[/bold cyan]\n")
        
        for match in matches[:3]:
            symbol = match["symbol"]
            paths = trace_call_chain(call_graph, symbol, depth)
            
            console.print(f"[green]Flow from {symbol}:[/green]")
            
            for path in paths[:5]:
                path_str = " → ".join(path)
                console.print(f"  {path_str}")
            
            if len(paths) > 5:
                console.print(f"  ... and {len(paths) - 5} more paths")
            console.print()


def handle_flow_command(console: Console, query: str, path: str, depth: int) -> None:
    """CLI handler for flow command - more detailed flow analysis."""
    from cortexcode.cli import require_index_path
    
    path, index_path = require_index_path(console, path)
    
    with open(index_path) as f:
        index_data = json.load(f)
    
    call_graph = index_data.get("call_graph", {})
    files = index_data.get("files", {})
    
    if not call_graph:
        console.print("[yellow]No call graph found in index[/yellow]")
        return
    
    # Split query into keywords
    keywords = [k.strip() for k in query.lower().split()]
    
    # Find all symbols that match any keyword
    related_symbols = []
    for symbol in call_graph.keys():
        symbol_lower = symbol.lower()
        if any(k in symbol_lower for k in keywords):
            related_symbols.append(symbol)
    
    if not related_symbols:
        console.print(f"[yellow]No symbols found matching any of: {keywords}[/yellow]")
        return
    
    # Build flow groups
    console.print(f"\n[bold cyan]Flow Analysis for '{query}':[/bold cyan]\n")
    
    # Group by file
    file_groups = {}
    for symbol in related_symbols:
        sym_context = get_symbol_context(index_data, symbol)
        file_path = sym_context.get("file", "unknown")
        if file_path not in file_groups:
            file_groups[file_path] = []
        file_groups[file_path].append({
            "symbol": symbol,
            "context": sym_context,
            "calls": call_graph.get(symbol, []),
        })
    
    for file_path, symbols in sorted(file_groups.items()):
        console.print(f"[green]📁 {file_path}[/green]")
        
        for sym in symbols[:5]:
            calls = sym["calls"]
            calls_str = ", ".join(calls[:3]) if calls else "no calls"
            console.print(f"   • {sym['symbol']} → {calls_str}")
        
        if len(symbols) > 5:
            console.print(f"   ... and {len(symbols) - 5} more")
        console.print()
    
    # Find entry points
    entry_points = find_entry_points(call_graph)
    related_entry_points = [ep for ep in entry_points if any(k in ep.lower() for k in keywords)]
    
    if related_entry_points:
        console.print("[bold]Likely Entry Points:[/bold]")
        for ep in related_entry_points[:5]:
            console.print(f"  • {ep}")
        console.print()
