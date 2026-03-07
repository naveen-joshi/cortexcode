import json
from typing import Any

from cortexcode.mcp.mcp_protocol import create_mcp_error, create_mcp_response
from cortexcode.mcp.mcp_registry import TOOL_HANDLERS


class MCPToolHandlersMixin:
    """Shared MCP tool dispatch and handler implementations."""

    def _project_root(self) -> str:
        return str(self.index_path.parent.parent)

    def _call_tool(self, req_id: Any, tool_name: str, args: dict) -> dict:
        """Execute a tool call."""
        self._reload_index()

        if not self.index:
            return create_mcp_response(req_id, {
                "content": [{"type": "text", "text": "Error: No index found. Run 'cortexcode index' first."}],
                "isError": True,
            })

        handler_name = TOOL_HANDLERS.get(tool_name)
        if not handler_name:
            return create_mcp_error(req_id, -32602, f"Unknown tool: {tool_name}")

        try:
            result = getattr(self, handler_name)(args)
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
            if file_path.lower() in rel_path.lower() and isinstance(file_data, dict):
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
        callers = [name for name, callees in call_graph.items() if symbol in callees]

        result = {
            "symbol": symbol,
            "calls": calls,
            "called_by": callers[:20],
        }

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
                    sym_type = sym.get("type", "unknown")
                    type_counts[sym_type] = type_counts.get(sym_type, 0) + 1

        non_empty_calls = sum(1 for calls in call_graph.values() if calls)

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
            "dead_code": dead[:limit],
        }

    def _tool_complexity(self, args: dict) -> dict:
        """Find most complex functions."""
        from cortexcode.analysis import compute_complexity

        limit = args.get("limit", 20)
        complex_funcs = compute_complexity(self.index, self._project_root())
        return {
            "count": len(complex_funcs),
            "complex_functions": complex_funcs[:limit],
        }

    def _tool_impact(self, args: dict) -> dict:
        """Analyze change impact of a symbol."""
        from cortexcode.analysis import analyze_change_impact

        symbol = args.get("symbol", "")
        if not symbol:
            return {"error": "symbol is required"}

        return analyze_change_impact(self.index, symbol)

    def _tool_file_deps(self, args: dict) -> dict:
        """Get file dependencies."""
        file_deps = self.index.get("file_dependencies", {})
        file_path = args.get("file_path", "")

        if file_path:
            for rel_path, deps in file_deps.items():
                if file_path.lower() in rel_path.lower():
                    imported_by = [
                        path for path, dependencies in file_deps.items()
                        if any(file_path.lower() in dependency.lower() for dependency in dependencies)
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
        duplicates = detect_duplicates(self.index, self._project_root(), min_lines)
        return {"count": len(duplicates), "duplicates": duplicates}

    def _tool_security_scan(self, args: dict) -> dict:
        """Scan for security issues."""
        from cortexcode.advanced_analysis import security_scan
        return security_scan(self._project_root(), self.index)

    def _tool_circular_deps(self, args: dict) -> dict:
        """Detect circular dependencies."""
        from cortexcode.advanced_analysis import detect_circular_deps

        cycles = detect_circular_deps(self.index)
        return {"count": len(cycles), "cycles": cycles}

    def _tool_endpoints(self, args: dict) -> dict:
        """Extract API endpoints."""
        from cortexcode.advanced_analysis import extract_endpoints
        return extract_endpoints(self.index, self._project_root())

    def _tool_api_docs(self, args: dict) -> dict:
        """Generate API documentation."""
        from cortexcode.advanced_analysis import generate_api_docs
        return generate_api_docs(self.index, self._project_root())
