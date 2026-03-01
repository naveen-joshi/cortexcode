"""LSP Server — Language Server Protocol support for CortexCode.

Provides hover, go-to-definition, and document symbols via LSP,
so any LSP-compatible editor can use CortexCode index data.

Usage:
    cortexcode lsp          # Start LSP server on stdin/stdout
"""

import json
import re
import sys
from pathlib import Path
from typing import Any


def _read_message(stream) -> dict | None:
    """Read an LSP message from stream (Content-Length header + JSON body)."""
    headers = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    
    content_length = int(headers.get("content-length", 0))
    if content_length == 0:
        return None
    
    body = stream.read(content_length)
    return json.loads(body)


def _write_message(stream, msg: dict) -> None:
    """Write an LSP message to stream."""
    body = json.dumps(msg)
    header = f"Content-Length: {len(body)}\r\n\r\n"
    stream.write(header + body)
    stream.flush()


def _make_response(req_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


class CortexCodeLSP:
    """Minimal LSP server backed by CortexCode index."""
    
    def __init__(self):
        self.index: dict | None = None
        self.index_path: Path | None = None
        self.root_path: str = ""
        self._symbol_cache: dict[str, list[dict]] = {}  # file -> symbols
    
    def _load_index(self):
        """Find and load the CortexCode index."""
        if self.root_path:
            candidate = Path(self.root_path) / ".cortexcode" / "index.json"
            if candidate.exists():
                self.index_path = candidate
                try:
                    self.index = json.loads(candidate.read_text(encoding="utf-8"))
                    self._build_symbol_cache()
                except (json.JSONDecodeError, OSError):
                    self.index = None
    
    def _build_symbol_cache(self):
        """Build a lookup from file path to symbols."""
        self._symbol_cache = {}
        if not self.index:
            return
        root = self.index.get("project_root", "")
        for rel_path, file_data in self.index.get("files", {}).items():
            if not isinstance(file_data, dict):
                continue
            # Store by both relative and absolute path
            abs_path = str(Path(root) / rel_path).replace("\\", "/")
            self._symbol_cache[abs_path] = file_data.get("symbols", [])
            self._symbol_cache[rel_path.replace("\\", "/")] = file_data.get("symbols", [])
    
    def _find_symbol_at(self, uri: str, line: int, col: int) -> dict | None:
        """Find a symbol at a given position."""
        file_path = _uri_to_path(uri)
        
        # Try to read the word at position from the file
        word = self._get_word_at_position(file_path, line, col)
        if not word:
            return None
        
        # Search all files for this symbol
        if self.index:
            for rel_path, file_data in self.index.get("files", {}).items():
                if not isinstance(file_data, dict):
                    continue
                for sym in file_data.get("symbols", []):
                    if sym.get("name") == word:
                        return {**sym, "file": rel_path}
                    # Check methods
                    for m in sym.get("methods", []):
                        if m.get("name") == word:
                            return {**m, "file": rel_path}
        return None
    
    def _get_word_at_position(self, file_path: str, line: int, col: int) -> str | None:
        """Extract the word under the cursor."""
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            lines = path.read_text(encoding="utf-8", errors="ignore").split("\n")
            if line >= len(lines):
                return None
            text = lines[line]
            # Find word boundaries
            start = col
            while start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_"):
                start -= 1
            end = col
            while end < len(text) and (text[end].isalnum() or text[end] == "_"):
                end += 1
            word = text[start:end]
            return word if word else None
        except (OSError, IndexError):
            return None
    
    def handle(self, msg: dict) -> dict | None:
        """Handle an LSP request/notification."""
        method = msg.get("method", "")
        params = msg.get("params", {})
        req_id = msg.get("id")
        
        if method == "initialize":
            self.root_path = params.get("rootPath", "") or ""
            root_uri = params.get("rootUri", "")
            if root_uri and not self.root_path:
                self.root_path = _uri_to_path(root_uri)
            self._load_index()
            
            return _make_response(req_id, {
                "capabilities": {
                    "hoverProvider": True,
                    "definitionProvider": True,
                    "documentSymbolProvider": True,
                    "textDocumentSync": 1,
                },
                "serverInfo": {
                    "name": "cortexcode-lsp",
                    "version": "0.1.0",
                },
            })
        
        elif method == "initialized":
            return None
        
        elif method == "shutdown":
            return _make_response(req_id, None)
        
        elif method == "exit":
            sys.exit(0)
        
        elif method == "textDocument/hover":
            return self._handle_hover(req_id, params)
        
        elif method == "textDocument/definition":
            return self._handle_definition(req_id, params)
        
        elif method == "textDocument/documentSymbol":
            return self._handle_document_symbols(req_id, params)
        
        elif req_id is not None:
            return _make_response(req_id, None)
        
        return None
    
    def _handle_hover(self, req_id, params: dict) -> dict:
        """Handle textDocument/hover."""
        uri = params.get("textDocument", {}).get("uri", "")
        pos = params.get("position", {})
        line = pos.get("line", 0)
        col = pos.get("character", 0)
        
        sym = self._find_symbol_at(uri, line, col)
        if not sym:
            return _make_response(req_id, None)
        
        # Build hover content
        parts = [f"**{sym.get('name')}** ({sym.get('type', 'symbol')})"]
        if sym.get("params"):
            parts.append(f"Parameters: `{', '.join(sym['params'])}`")
        if sym.get("return_type"):
            parts.append(f"Returns: `{sym['return_type']}`")
        if sym.get("file"):
            parts.append(f"Defined in: `{sym['file']}:{sym.get('line', '?')}`")
        if sym.get("calls"):
            parts.append(f"Calls: {', '.join(f'`{c}`' for c in sym['calls'][:5])}")
        if sym.get("doc"):
            parts.append(f"\n{sym['doc']}")
        if sym.get("framework"):
            parts.append(f"Framework: {sym['framework']}")
        
        content = "\n\n".join(parts)
        
        return _make_response(req_id, {
            "contents": {"kind": "markdown", "value": content},
        })
    
    def _handle_definition(self, req_id, params: dict) -> dict:
        """Handle textDocument/definition."""
        uri = params.get("textDocument", {}).get("uri", "")
        pos = params.get("position", {})
        line = pos.get("line", 0)
        col = pos.get("character", 0)
        
        sym = self._find_symbol_at(uri, line, col)
        if not sym or not sym.get("file"):
            return _make_response(req_id, None)
        
        root = self.index.get("project_root", "") if self.index else ""
        target_path = str(Path(root) / sym["file"])
        target_uri = _path_to_uri(target_path)
        target_line = max(0, sym.get("line", 1) - 1)
        
        return _make_response(req_id, {
            "uri": target_uri,
            "range": {
                "start": {"line": target_line, "character": 0},
                "end": {"line": target_line, "character": 0},
            },
        })
    
    def _handle_document_symbols(self, req_id, params: dict) -> dict:
        """Handle textDocument/documentSymbol."""
        uri = params.get("textDocument", {}).get("uri", "")
        file_path = _uri_to_path(uri).replace("\\", "/")
        
        symbols = []
        
        # Try to find symbols for this file
        found_syms = self._symbol_cache.get(file_path, [])
        if not found_syms:
            # Try matching by filename
            for key, syms in self._symbol_cache.items():
                if file_path.endswith(key) or key.endswith(file_path.split("/")[-1]):
                    found_syms = syms
                    break
        
        symbol_kind_map = {
            "function": 12,  # Function
            "method": 6,     # Method
            "class": 5,      # Class
            "interface": 11, # Interface
            "type": 26,      # TypeParameter
            "enum": 10,      # Enum
        }
        
        for sym in found_syms:
            line = max(0, sym.get("line", 1) - 1)
            kind = symbol_kind_map.get(sym.get("type", ""), 13)  # 13 = Variable
            
            symbols.append({
                "name": sym.get("name", "?"),
                "kind": kind,
                "range": {
                    "start": {"line": line, "character": 0},
                    "end": {"line": line, "character": 0},
                },
                "selectionRange": {
                    "start": {"line": line, "character": 0},
                    "end": {"line": line, "character": 0},
                },
            })
        
        return _make_response(req_id, symbols)


def _uri_to_path(uri: str) -> str:
    """Convert file URI to path."""
    if uri.startswith("file:///"):
        path = uri[8:]  # Remove file:///
        # Handle Windows drive letters
        if len(path) > 2 and path[1] == ":" or (path[0] == "/" and len(path) > 3 and path[2] == ":"):
            path = path.lstrip("/")
        return path.replace("/", "\\") if "\\" in path or ":" in path[:3] else path
    return uri


def _path_to_uri(path: str) -> str:
    """Convert path to file URI."""
    path = path.replace("\\", "/")
    if not path.startswith("/"):
        path = "/" + path
    return "file://" + path


def run_lsp_server():
    """Run the LSP server on stdin/stdout."""
    server = CortexCodeLSP()
    
    # Use binary mode for reading
    stdin = sys.stdin
    stdout = sys.stdout
    
    while True:
        msg = _read_message(stdin)
        if msg is None:
            break
        
        response = server.handle(msg)
        if response is not None:
            _write_message(stdout, response)
