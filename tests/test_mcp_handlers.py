"""Tests for cortexcode.mcp MCP tool dispatch and handlers."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from cortexcode.mcp.mcp_server import CortexCodeMCPServer


_INDEX = {
    "project_root": "/tmp/test",
    "last_indexed": "2025-01-01T00:00:00",
    "languages": ["python"],
    "files": {
        "src/auth.py": {
            "symbols": [
                {"name": "authenticate", "type": "function", "line": 1,
                 "params": ["token"], "calls": ["verify_token"]},
                {"name": "hash_password", "type": "function", "line": 20,
                 "params": ["password"], "calls": []},
            ],
            "imports": [],
            "exports": [],
            "api_routes": [],
            "entities": [],
        },
        "src/models.py": {
            "symbols": [
                {"name": "UserModel", "type": "class", "line": 1,
                 "params": [], "calls": []},
            ],
            "imports": [],
            "exports": [],
            "api_routes": [],
            "entities": [],
        },
    },
    "call_graph": {"authenticate": ["verify_token"]},
    "file_dependencies": {"src/auth.py": ["src/models.py"]},
    "file_hashes": {},
}


@pytest.fixture
def server(tmp_path):
    index_path = tmp_path / ".cortexcode" / "index.json"
    index_path.parent.mkdir()
    index_path.write_text(json.dumps(_INDEX))
    return CortexCodeMCPServer(index_path)


# ── Protocol ──────────────────────────────────────────────────────────────────

def test_initialize(server):
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    resp = server.handle_request(req)
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    assert resp["result"]["serverInfo"]["name"] == "cortexcode"


def test_tools_list(server):
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    resp = server.handle_request(req)
    tool_names = {t["name"] for t in resp["result"]["tools"]}
    assert "cortexcode_search" in tool_names
    assert "cortexcode_context" in tool_names
    assert "cortexcode_stats" in tool_names


def test_unknown_method(server):
    req = {"jsonrpc": "2.0", "id": 3, "method": "nonexistent/method", "params": {}}
    resp = server.handle_request(req)
    assert "error" in resp


def test_notifications_initialized_returns_none(server):
    req = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    resp = server.handle_request(req)
    assert resp is None


def test_ping(server):
    req = {"jsonrpc": "2.0", "id": 4, "method": "ping", "params": {}}
    resp = server.handle_request(req)
    assert "result" in resp


# ── Tool: cortexcode_search ───────────────────────────────────────────────────

def _call_tool(server, tool_name, args):
    req = {
        "jsonrpc": "2.0",
        "id": 99,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": args},
    }
    resp = server.handle_request(req)
    content_text = resp["result"]["content"][0]["text"]
    return json.loads(content_text)


def test_search_finds_exact(server):
    results = _call_tool(server, "cortexcode_search", {"query": "authenticate"})
    names = [r["name"] for r in results]
    assert "authenticate" in names


def test_search_limit(server):
    results = _call_tool(server, "cortexcode_search", {"query": "auth", "limit": 1})
    assert len(results) <= 1


def test_search_type_filter(server):
    results = _call_tool(server, "cortexcode_search", {"query": "UserModel", "type": "class"})
    assert all(r["type"] == "class" for r in results)


def test_search_no_results(server):
    results = _call_tool(server, "cortexcode_search", {"query": "zzz_nonexistent"})
    assert results == []


# ── Tool: cortexcode_stats ────────────────────────────────────────────────────

def test_stats(server):
    stats = _call_tool(server, "cortexcode_stats", {})
    assert "symbols" in stats
    assert stats["symbols"] == 3
    assert stats["files"] == 2


# ── Tool: cortexcode_file_symbols ─────────────────────────────────────────────

def test_file_symbols(server):
    result = _call_tool(server, "cortexcode_file_symbols", {"file_path": "src/auth.py"})
    names = [s["name"] for s in result.get("symbols", [])]
    assert "authenticate" in names
    assert "hash_password" in names


def test_file_symbols_not_found(server):
    result = _call_tool(server, "cortexcode_file_symbols", {"file_path": "nonexistent.py"})
    assert "error" in result or result.get("symbols") == []


# ── Tool: cortexcode_call_graph ───────────────────────────────────────────────

def test_call_graph(server):
    result = _call_tool(server, "cortexcode_call_graph", {"symbol": "authenticate"})
    assert "calls" in result
    assert "verify_token" in result["calls"]


# ── Tool: cortexcode_file_deps ────────────────────────────────────────────────

def test_file_deps(server):
    result = _call_tool(server, "cortexcode_file_deps", {})
    assert "src/auth.py" in result.get("file_dependencies", {})


def test_file_deps_specific(server):
    result = _call_tool(server, "cortexcode_file_deps", {"file_path": "src/auth.py"})
    assert "src/models.py" in result.get("imports_from", [])


# ── Tool: unknown tool ────────────────────────────────────────────────────────

def test_unknown_tool_returns_error(server):
    req = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {"name": "cortexcode_does_not_exist", "arguments": {}},
    }
    resp = server.handle_request(req)
    assert "error" in resp


# ── Workspace tools ───────────────────────────────────────────────────────────

def _make_workspace_fixture(tmp_path):
    """Build a small two-repo workspace + a per-repo index for the MCP server."""
    import yaml

    shared_index = {
        "files": {
            "src/api.ts": {
                "symbols": [{"name": "getUser", "type": "function", "line": 1, "calls": []}],
                "imports": [],
            }
        },
        "call_graph": {},
        "file_dependencies": {},
    }
    fe_index = {
        "files": {
            "src/page.tsx": {
                "symbols": [{"name": "Page", "type": "function", "line": 1, "calls": ["getUser"]}],
                "imports": ["getUser from @acme/shared"],
            }
        },
        "call_graph": {"Page": ["getUser"]},
        "file_dependencies": {},
    }

    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "package.json").write_text(json.dumps({"name": "@acme/shared"}))
    (shared / ".cortexcode").mkdir()
    (shared / ".cortexcode" / "index.json").write_text(json.dumps(shared_index))

    fe = tmp_path / "fe"
    fe.mkdir()
    (fe / "package.json").write_text(json.dumps({
        "name": "@acme/fe",
        "dependencies": {"@acme/shared": "*"},
    }))
    (fe / ".cortexcode").mkdir()
    (fe / ".cortexcode" / "index.json").write_text(json.dumps(fe_index))

    (tmp_path / "cortexcode-workspace.yml").write_text(yaml.safe_dump({
        "name": "acme",
        "repos": [
            {"id": "shared", "path": str(shared), "package": "@acme/shared"},
            {"id": "fe", "path": str(fe), "package": "@acme/fe"},
        ],
    }))

    # The MCP server's `index_path.parent.parent` is used as the discovery root,
    # so put the per-repo index under tmp_path/.cortexcode/.
    (tmp_path / ".cortexcode").mkdir()
    (tmp_path / ".cortexcode" / "index.json").write_text(json.dumps(_INDEX))
    return tmp_path / ".cortexcode" / "index.json"


def test_workspace_repos_tool(tmp_path):
    index_path = _make_workspace_fixture(tmp_path)
    server = CortexCodeMCPServer(index_path)
    result = _call_tool(server, "cortexcode_workspace_repos", {})
    ids = {r["id"] for r in result["repos"]}
    assert ids == {"shared", "fe"}


def test_workspace_search_tool(tmp_path):
    index_path = _make_workspace_fixture(tmp_path)
    server = CortexCodeMCPServer(index_path)
    result = _call_tool(server, "cortexcode_workspace_search", {"query": "getUser"})
    repos = {r["repo"] for r in result["results"]}
    assert "shared" in repos


def test_workspace_deps_tool(tmp_path):
    index_path = _make_workspace_fixture(tmp_path)
    server = CortexCodeMCPServer(index_path)

    from cortexcode.workspace import Workspace
    ws = Workspace(tmp_path)
    ws.load_config()
    ws.build_linkage()

    result = _call_tool(server, "cortexcode_workspace_deps", {})
    assert "shared" in result["graph"]["fe"]


def test_workspace_impact_tool(tmp_path):
    index_path = _make_workspace_fixture(tmp_path)
    server = CortexCodeMCPServer(index_path)
    # Need linkage to discover consumers
    from cortexcode.workspace import Workspace
    ws = Workspace(tmp_path)
    ws.load_config()
    ws.build_linkage()

    result = _call_tool(server, "cortexcode_workspace_impact", {"ref": "shared:getUser"})
    assert result["consumers"] == ["fe"]


def test_workspace_tool_when_no_workspace(tmp_path):
    # Set up a server with a per-repo index but NO workspace config.
    index_path = tmp_path / ".cortexcode" / "index.json"
    index_path.parent.mkdir()
    index_path.write_text(json.dumps(_INDEX))
    server = CortexCodeMCPServer(index_path)

    result = _call_tool(server, "cortexcode_workspace_repos", {})
    assert "error" in result


# ── No index ──────────────────────────────────────────────────────────────────

def test_no_index_returns_error(tmp_path):
    missing_path = tmp_path / ".cortexcode" / "index.json"
    server = CortexCodeMCPServer(missing_path)
    req = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {"name": "cortexcode_stats", "arguments": {}},
    }
    resp = server.handle_request(req)
    content = resp["result"]["content"][0]["text"]
    assert "No index" in content or "error" in content.lower()
