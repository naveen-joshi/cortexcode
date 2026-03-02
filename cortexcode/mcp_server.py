"""MCP Server — Model Context Protocol server for AI agent integration.

Provides tools for AI agents to query the CortexCode index directly.
Supports: symbol lookup, file context, call graph traversal, diff context.

Usage:
    cortexcode mcp                    # Start MCP server on stdin/stdout
    cortexcode mcp --port 8080        # Start on HTTP port
"""

import json
import sys
from pathlib import Path
from typing import Any


def create_mcp_response(id: Any, result: Any) -> dict:
    """Create a JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": id, "result": result}


def create_mcp_error(id: Any, code: int, message: str) -> dict:
    """Create a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def load_index(index_path: Path) -> dict | None:
    """Load index from disk."""
    try:
        if index_path.exists():
            return json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return None


def auto_index_project(root_path: Path) -> bool:
    """Auto-index the project if no index exists."""
    from cortexcode.indexer import CodeIndexer
    
    index_path = root_path / ".cortexcode" / "index.json"
    if index_path.exists():
        return True
    
    try:
        print(f"CortexCode: Auto-indexing {root_path}...", file=sys.stderr)
        indexer = CodeIndexer()
        indexer.index_directory(root_path)
        
        output_dir = root_path / ".cortexcode"
        output_dir.mkdir(parents=True, exist_ok=True)
        indexer.save_index(output_dir / "index.json")
        print(f"CortexCode: Index created successfully", file=sys.stderr)
        return True
    except Exception as e:
        print(f"CortexCode: Auto-index failed: {e}", file=sys.stderr)
        return False


class CortexCodeMCPServer:
    """MCP server that exposes CortexCode index as tools."""
    
    def __init__(self, index_path: Path | None = None):
        self.index_path = index_path or Path(".cortexcode/index.json")
        self.index: dict | None = None
        self._reload_index()
    
    def _reload_index(self):
        """Reload the index from disk, auto-index if needed."""
        self.index = load_index(self.index_path)
        
        # If no index, try to auto-index
        if not self.index and self.index_path.parent.exists():
            root = self.index_path.parent.parent
            if auto_index_project(root):
                self.index = load_index(self.index_path)
    
    def handle_request(self, request: dict) -> dict:
        """Handle a JSON-RPC 2.0 request."""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")
        
        if method == "initialize":
            return create_mcp_response(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "cortexcode",
                    "version": "0.1.0",
                },
            })
        
        elif method == "notifications/initialized":
            return None  # No response needed for notifications
        
        elif method == "tools/list":
            return create_mcp_response(req_id, {
                "tools": self._get_tools(),
            })
        
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            return self._call_tool(req_id, tool_name, tool_args)
        
        elif method == "ping":
            return create_mcp_response(req_id, {})
        
        else:
            return create_mcp_error(req_id, -32601, f"Method not found: {method}")
    
    def _get_tools(self) -> list[dict]:
        """Return list of available tools."""
        return [
            {
                "name": "cortexcode_search",
                "description": "USE THIS when user asks to find, locate, search for a function, class, method, or any code symbol. Also use when you need to know where something is defined. Returns type, file, line, params, and calls.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What to search for - function name, class name, or any code symbol"},
                        "type": {"type": "string", "description": "Filter by type: function, class, method, interface", "enum": ["function", "class", "method", "interface"]},
                        "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "cortexcode_context",
                "description": "USE THIS when you need to understand how a function/class works, see its implementation, or see what it calls/who calls it. Also use when user asks 'how does X work' or 'show me the code for X'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Symbol name to get context for, or 'file:symbol' for specific file"},
                        "num_results": {"type": "integer", "description": "Number of results", "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "cortexcode_file_symbols",
                "description": "USE THIS when you need to see all functions/classes in a specific file, or understand what a file exports/defines.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Relative file path (e.g. 'src/auth.ts')"},
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "cortexcode_call_graph",
                "description": "USE THIS when you need to trace what functions call what, or find all callers of a function. Also use when user asks 'what uses this function' or 'where is this called'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Symbol name to trace"},
                        "depth": {"type": "integer", "description": "Depth of traversal (default 1)", "default": 1},
                    },
                    "required": ["symbol"],
                },
            },
            {
                "name": "cortexcode_diff",
                "description": "USE THIS when you need to find what code changed, or see modified functions. Also use when user asks 'what changed' or 'what was modified recently'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "ref": {"type": "string", "description": "Git ref to compare against (default HEAD)", "default": "HEAD"},
                    },
                },
            },
            {
                "name": "cortexcode_stats",
                "description": "USE THIS when user asks about project size, file count, language distribution, or wants to know 'how big is the project'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "cortexcode_deadcode",
                "description": "USE THIS when user asks to find unused, unreachable, or dead code. Also use when user asks 'what functions are not used' or 'show me dead code'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
                    },
                },
            },
            {
                "name": "cortexcode_complexity",
                "description": "USE THIS when user asks about code complexity, most complex functions, or which functions are hard to maintain. Also use when user asks 'what is the most complex code' or 'show me complex functions'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
                    },
                },
            },
            {
                "name": "cortexcode_impact",
                "description": "USE THIS when user asks about change impact, what would break if they modify something, or which functions depend on a symbol. Also use when user asks 'what will break if I change X' or 'show me what uses this function'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Symbol name to analyze impact for"},
                    },
                    "required": ["symbol"],
                },
            },
            {
                "name": "cortexcode_file_deps",
                "description": "USE THIS when you need to find what files import from what, or trace file dependencies. Also use when user asks 'what does this file depend on'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "File to check dependencies for (optional, returns all if omitted)"},
                    },
                },
            },
            {
                "name": "cortexcode_fuzzy_search",
                "description": "USE THIS when exact search returns no results, or user has a typo or partial name. Fuzzy search finds approximate matches using similarity scoring.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Approximate symbol name to search for"},
                        "threshold": {"type": "number", "description": "Minimum similarity score 0-1 (default 0.5)", "default": 0.5},
                        "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "cortexcode_regex_search",
                "description": "USE THIS when user wants to search with a pattern, like 'find all getters' or 'functions starting with handle'. Supports regex patterns.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Regex pattern to match symbol names (e.g. '^get.*', 'handle.*Request$')"},
                        "type": {"type": "string", "description": "Filter by type: function, class, method, interface", "enum": ["function", "class", "method", "interface"]},
                        "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
                    },
                    "required": ["pattern"],
                },
            },
            {
                "name": "cortexcode_duplicates",
                "description": "USE THIS when user asks about code duplication, copy-paste code, or repeated logic. Finds exact and near-duplicate functions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "min_lines": {"type": "integer", "description": "Minimum function lines to consider (default 5)", "default": 5},
                    },
                },
            },
            {
                "name": "cortexcode_security_scan",
                "description": "USE THIS when user asks about security issues, vulnerabilities, hardcoded secrets, SQL injection, or XSS risks. Scans source code for common security problems.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "cortexcode_circular_deps",
                "description": "USE THIS when user asks about circular dependencies, import cycles, or dependency loops.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "cortexcode_endpoints",
                "description": "USE THIS when user asks about API endpoints, routes, REST APIs, or wants a list of all URLs/paths in the app. Detects Express, Flask, FastAPI, Django, Next.js, Spring, Go, Rails routes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "cortexcode_api_docs",
                "description": "USE THIS when user asks to generate documentation, see doc coverage, or find undocumented functions. Auto-generates API docs from signatures and docstrings.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]
    
    def _call_tool(self, req_id: Any, tool_name: str, args: dict) -> dict:
        """Execute a tool call."""
        self._reload_index()
        
        if not self.index:
            return create_mcp_response(req_id, {
                "content": [{"type": "text", "text": "Error: No index found. Run 'cortexcode index' first."}],
                "isError": True,
            })
        
        try:
            if tool_name == "cortexcode_search":
                result = self._tool_search(args)
            elif tool_name == "cortexcode_context":
                result = self._tool_context(args)
            elif tool_name == "cortexcode_file_symbols":
                result = self._tool_file_symbols(args)
            elif tool_name == "cortexcode_call_graph":
                result = self._tool_call_graph(args)
            elif tool_name == "cortexcode_diff":
                result = self._tool_diff(args)
            elif tool_name == "cortexcode_stats":
                result = self._tool_stats(args)
            elif tool_name == "cortexcode_deadcode":
                result = self._tool_deadcode(args)
            elif tool_name == "cortexcode_complexity":
                result = self._tool_complexity(args)
            elif tool_name == "cortexcode_impact":
                result = self._tool_impact(args)
            elif tool_name == "cortexcode_file_deps":
                result = self._tool_file_deps(args)
            elif tool_name == "cortexcode_fuzzy_search":
                result = self._tool_fuzzy_search(args)
            elif tool_name == "cortexcode_regex_search":
                result = self._tool_regex_search(args)
            elif tool_name == "cortexcode_duplicates":
                result = self._tool_duplicates(args)
            elif tool_name == "cortexcode_security_scan":
                result = self._tool_security_scan(args)
            elif tool_name == "cortexcode_circular_deps":
                result = self._tool_circular_deps(args)
            elif tool_name == "cortexcode_endpoints":
                result = self._tool_endpoints(args)
            elif tool_name == "cortexcode_api_docs":
                result = self._tool_api_docs(args)
            else:
                return create_mcp_error(req_id, -32602, f"Unknown tool: {tool_name}")
            
            return create_mcp_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            })
        except Exception as e:
            return create_mcp_response(req_id, {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True,
            })
    
    def _tool_search(self, args: dict) -> list[dict]:
        """Search symbols by name."""
        query = args.get("query", "").lower()
        sym_type = args.get("type")
        limit = args.get("limit", 10)
        
        files = self.index.get("files", {})
        results = []
        
        for rel_path, file_data in files.items():
            if not isinstance(file_data, dict):
                continue
            for sym in file_data.get("symbols", []):
                name = sym.get("name", "").lower()
                if query in name:
                    if sym_type and sym.get("type") != sym_type:
                        continue
                    results.append({
                        "name": sym.get("name"),
                        "type": sym.get("type"),
                        "file": rel_path,
                        "line": sym.get("line"),
                        "params": sym.get("params", []),
                        "doc": sym.get("doc"),
                    })
        
        return results[:limit]
    
    def _tool_context(self, args: dict) -> dict:
        """Get context for a symbol."""
        from cortexcode.context import get_context
        return get_context(self.index_path, args.get("query"), args.get("num_results", 5))
    
    def _tool_file_symbols(self, args: dict) -> dict:
        """List all symbols in a file."""
        file_path = args.get("file_path", "")
        files = self.index.get("files", {})
        
        for rel_path, file_data in files.items():
            if file_path.lower() in rel_path.lower():
                if isinstance(file_data, dict):
                    return {
                        "file": rel_path,
                        "symbols": file_data.get("symbols", []),
                        "imports": file_data.get("imports", []),
                        "exports": file_data.get("exports", []),
                    }
        
        return {"error": f"File not found: {file_path}"}
    
    def _tool_call_graph(self, args: dict) -> dict:
        """Get call graph for a symbol."""
        symbol = args.get("symbol", "")
        depth = args.get("depth", 1)
        call_graph = self.index.get("call_graph", {})
        
        calls = call_graph.get(symbol, [])
        callers = [name for name, c in call_graph.items() if symbol in c]
        
        result = {
            "symbol": symbol,
            "calls": calls,
            "called_by": callers[:20],
        }
        
        # Depth > 1: also get calls of callees
        if depth > 1 and calls:
            result["transitive_calls"] = {}
            for callee in calls[:10]:
                sub_calls = call_graph.get(callee, [])
                if sub_calls:
                    result["transitive_calls"][callee] = sub_calls
        
        return result
    
    def _tool_diff(self, args: dict) -> dict:
        """Get diff context."""
        from cortexcode.git_diff import get_diff_context
        return get_diff_context(self.index_path, args.get("ref", "HEAD"))
    
    def _tool_stats(self, args: dict) -> dict:
        """Get project stats."""
        files = self.index.get("files", {})
        call_graph = self.index.get("call_graph", {})
        
        total_symbols = 0
        type_counts = {}
        for file_data in files.values():
            if isinstance(file_data, dict):
                for sym in file_data.get("symbols", []):
                    total_symbols += 1
                    t = sym.get("type", "unknown")
                    type_counts[t] = type_counts.get(t, 0) + 1
        
        non_empty_calls = sum(1 for v in call_graph.values() if v)
        
        return {
            "files": len(files),
            "symbols": total_symbols,
            "symbol_types": type_counts,
            "languages": self.index.get("languages", []),
            "call_graph_entries": len(call_graph),
            "symbols_with_calls": non_empty_calls,
            "file_dependencies": len(self.index.get("file_dependencies", {})),
            "last_indexed": self.index.get("last_indexed"),
        }
    
    def _tool_deadcode(self, args: dict) -> dict:
        """Find potentially dead code."""
        from cortexcode.analysis import detect_dead_code
        
        limit = args.get("limit", 20)
        dead = detect_dead_code(self.index)
        
        return {
            "count": len(dead),
            "dead_code": dead[:limit]
        }
    
    def _tool_complexity(self, args: dict) -> dict:
        """Find most complex functions."""
        from cortexcode.analysis import compute_complexity
        
        limit = args.get("limit", 20)
        complex_funcs = compute_complexity(self.index, str(self.index_path.parent.parent))
        
        return {
            "count": len(complex_funcs),
            "complex_functions": complex_funcs[:limit]
        }
    
    def _tool_impact(self, args: dict) -> dict:
        """Analyze change impact of a symbol."""
        from cortexcode.analysis import analyze_change_impact
        
        symbol = args.get("symbol", "")
        if not symbol:
            return {"error": "symbol is required"}
        
        impact = analyze_change_impact(self.index, symbol)
        return impact
    
    def _tool_file_deps(self, args: dict) -> dict:
        """Get file dependencies."""
        file_deps = self.index.get("file_dependencies", {})
        file_path = args.get("file_path", "")
        
        if file_path:
            for rel_path, deps in file_deps.items():
                if file_path.lower() in rel_path.lower():
                    # Also find reverse deps (who imports this file)
                    imported_by = [
                        p for p, d in file_deps.items() 
                        if any(file_path.lower() in dep.lower() for dep in d)
                    ]
                    return {
                        "file": rel_path,
                        "imports_from": deps,
                        "imported_by": imported_by,
                    }
            return {"error": f"No dependencies found for: {file_path}"}
        
        return {"file_dependencies": file_deps}
    
    def _tool_fuzzy_search(self, args: dict) -> dict:
        """Fuzzy search for symbols."""
        from cortexcode.advanced_analysis import fuzzy_search
        
        query = args.get("query", "")
        threshold = args.get("threshold", 0.5)
        limit = args.get("limit", 20)
        
        results = fuzzy_search(self.index, query, threshold, limit)
        return {"count": len(results), "results": results}
    
    def _tool_regex_search(self, args: dict) -> dict:
        """Regex search for symbols."""
        from cortexcode.advanced_analysis import regex_search
        
        pattern = args.get("pattern", "")
        sym_type = args.get("type")
        limit = args.get("limit", 20)
        
        results = regex_search(self.index, pattern, sym_type, limit)
        return {"count": len(results), "results": results}
    
    def _tool_duplicates(self, args: dict) -> dict:
        """Find duplicate code."""
        from cortexcode.advanced_analysis import detect_duplicates
        
        min_lines = args.get("min_lines", 5)
        root = str(self.index_path.parent.parent)
        
        dupes = detect_duplicates(self.index, root, min_lines)
        return {"count": len(dupes), "duplicates": dupes}
    
    def _tool_security_scan(self, args: dict) -> dict:
        """Scan for security issues."""
        from cortexcode.advanced_analysis import security_scan
        
        root = str(self.index_path.parent.parent)
        return security_scan(root, self.index)
    
    def _tool_circular_deps(self, args: dict) -> dict:
        """Detect circular dependencies."""
        from cortexcode.advanced_analysis import detect_circular_deps
        
        cycles = detect_circular_deps(self.index)
        return {"count": len(cycles), "cycles": cycles}
    
    def _tool_endpoints(self, args: dict) -> dict:
        """Extract API endpoints."""
        from cortexcode.advanced_analysis import extract_endpoints
        
        root = str(self.index_path.parent.parent)
        return extract_endpoints(self.index, root)
    
    def _tool_api_docs(self, args: dict) -> dict:
        """Generate API documentation."""
        from cortexcode.advanced_analysis import generate_api_docs
        
        root = str(self.index_path.parent.parent)
        return generate_api_docs(self.index, root)


def run_stdio_server(index_path: Path | None = None):
    """Run MCP server on stdin/stdout (standard MCP transport)."""
    server = CortexCodeMCPServer(index_path)
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = create_mcp_error(None, -32700, "Parse error")
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            continue
        
        response = server.handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
