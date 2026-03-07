"""MCP Server — Model Context Protocol server for AI agent integration.

Provides tools for AI agents to query the CortexCode index directly.
Supports: symbol lookup, file context, call graph traversal, diff context.

Usage:
    cortexcode mcp                    # Start MCP server on stdin/stdout
    cortexcode mcp --port 8080        # Start on HTTP port
"""

from pathlib import Path
from cortexcode.mcp.mcp_protocol import create_mcp_error, create_mcp_response
from cortexcode.mcp.mcp_registry import get_mcp_tools
from cortexcode.mcp.mcp_tool_handlers import MCPToolHandlersMixin
from cortexcode.mcp.mcp_transport import auto_index_project, load_index, run_stdio_transport


class CortexCodeMCPServer(MCPToolHandlersMixin):
    """MCP server that exposes CortexCode index as tools."""

    def __init__(self, index_path: Path | None = None):
        self.index_path = index_path or Path(".cortexcode/index.json")
        self.index: dict | None = None
        self._reload_index()

    def _reload_index(self):
        """Reload the index from disk, auto-index if needed."""
        self.index = load_index(self.index_path)

        if not self.index and self.index_path.parent.exists():
            root = self.index_path.parent.parent
            if auto_index_project(root):
                self.index = load_index(self.index_path)

    def handle_request(self, request: dict) -> dict | None:
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

        if method == "notifications/initialized":
            return None

        if method == "tools/list":
            return create_mcp_response(req_id, {
                "tools": self._get_tools(),
            })

        if method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            return self._call_tool(req_id, tool_name, tool_args)

        if method == "ping":
            return create_mcp_response(req_id, {})

        return create_mcp_error(req_id, -32601, f"Method not found: {method}")

    def _get_tools(self) -> list[dict]:
        """Return list of available tools."""
        return get_mcp_tools()


def run_stdio_server(index_path: Path | None = None):
    """Run MCP server on stdin/stdout (standard MCP transport)."""
    run_stdio_transport(CortexCodeMCPServer, index_path)
