"""MCP (Model Context Protocol) server implementation."""

from cortexcode.mcp.mcp_protocol import create_mcp_error, create_mcp_response
from cortexcode.mcp.mcp_registry import TOOL_HANDLERS, get_mcp_tools
from cortexcode.mcp.mcp_tool_handlers import MCPToolHandlersMixin
from cortexcode.mcp.mcp_transport import auto_index_project, load_index, run_stdio_transport
from cortexcode.mcp.mcp_server import CortexCodeMCPServer, run_stdio_server

__all__ = [
    "create_mcp_error",
    "create_mcp_response",
    "TOOL_HANDLERS",
    "get_mcp_tools",
    "MCPToolHandlersMixin",
    "auto_index_project",
    "load_index",
    "run_stdio_transport",
    "CortexCodeMCPServer",
    "run_stdio_server",
]
