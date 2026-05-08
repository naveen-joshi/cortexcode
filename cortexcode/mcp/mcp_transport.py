import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from cortexcode.mcp.mcp_protocol import create_mcp_error


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
        print("CortexCode: Index created successfully", file=sys.stderr)
        return True
    except Exception as e:
        print(f"CortexCode: Auto-index failed: {e}", file=sys.stderr)
        return False


def run_stdio_transport(server_factory, index_path: Path | None = None) -> None:
    """Run MCP server on stdin/stdout."""
    server = server_factory(index_path)

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


def run_http_transport(server_factory, port: int, index_path: Path | None = None) -> None:
    """Run MCP server over HTTP on the given port.

    Accepts POST / with a JSON-RPC 2.0 body; responds with JSON.
    Allows any origin so browser-based tools can connect directly.
    """
    mcp_server = server_factory(index_path)

    class _Handler(BaseHTTPRequestHandler):
        def do_OPTIONS(self):
            self._send_cors_headers(200)
            self.end_headers()

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            try:
                request = json.loads(body)
            except json.JSONDecodeError:
                response = create_mcp_error(None, -32700, "Parse error")
                self._respond(response)
                return

            response = mcp_server.handle_request(request)
            self._respond(response if response is not None else {})

        def _respond(self, data: dict) -> None:
            payload = json.dumps(data).encode()
            self._send_cors_headers(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_cors_headers(self, status: int) -> None:
            self.send_response(status)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def log_message(self, fmt, *args):  # silence default access log
            pass

    httpd = HTTPServer(("", port), _Handler)
    print(f"CortexCode MCP server listening on http://localhost:{port}", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
