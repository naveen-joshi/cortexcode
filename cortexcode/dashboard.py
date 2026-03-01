"""Live dashboard server with auto-refresh on file changes."""

import json
import http.server
import threading
import hashlib
import time
from pathlib import Path
from typing import Any


class DashboardServer:
    """HTTP server that serves the HTML report and auto-regenerates on index changes."""
    
    def __init__(self, project_path: Path, port: int = 8787):
        self.project_path = project_path.resolve()
        self.port = port
        self.docs_dir = self.project_path / ".cortexcode" / "docs"
        self.index_path = self.project_path / ".cortexcode" / "index.json"
        self._last_hash: str = ""
        self._running = False
        self._server: http.server.HTTPServer | None = None
        self._poll_interval = 2.0  # seconds
    
    def _get_index_hash(self) -> str:
        """Get hash of the index file for change detection."""
        try:
            return hashlib.md5(self.index_path.read_bytes()).hexdigest()
        except OSError:
            return ""
    
    def _regenerate_docs(self) -> bool:
        """Regenerate HTML docs from the current index."""
        try:
            from cortexcode.docs import generate_all_docs
            generate_all_docs(self.index_path, self.docs_dir)
            return True
        except Exception as e:
            print(f"Failed to regenerate docs: {e}")
            return False
    
    def _ensure_docs(self) -> bool:
        """Ensure docs exist, generating if needed."""
        html_file = self.docs_dir / "index.html"
        if not html_file.exists():
            return self._regenerate_docs()
        return True
    
    def _inject_auto_refresh(self) -> None:
        """Inject auto-refresh script into the HTML report."""
        html_file = self.docs_dir / "index.html"
        if not html_file.exists():
            return
        
        content = html_file.read_text(encoding="utf-8")
        
        # Don't inject twice
        if "cortexcode-auto-refresh" in content:
            return
        
        refresh_script = f"""
<script id="cortexcode-auto-refresh">
(function() {{
    let lastHash = '';
    async function checkForUpdates() {{
        try {{
            const resp = await fetch('/__cortexcode_hash');
            const hash = await resp.text();
            if (lastHash && hash !== lastHash) {{
                console.log('Index changed, reloading...');
                location.reload();
            }}
            lastHash = hash;
        }} catch(e) {{}}
    }}
    setInterval(checkForUpdates, {int(self._poll_interval * 1000)});
    checkForUpdates();
}})();
</script>
"""
        content = content.replace("</body>", f"{refresh_script}</body>")
        html_file.write_text(content, encoding="utf-8")
    
    def _poll_for_changes(self) -> None:
        """Background thread that watches for index changes and regenerates docs."""
        while self._running:
            time.sleep(self._poll_interval)
            current_hash = self._get_index_hash()
            if current_hash and current_hash != self._last_hash:
                self._last_hash = current_hash
                self._regenerate_docs()
                self._inject_auto_refresh()
    
    def start(self, open_browser: bool = True) -> None:
        """Start the dashboard server."""
        if not self.index_path.exists():
            raise FileNotFoundError(f"No index found at {self.index_path}. Run `cortexcode index` first.")
        
        self._ensure_docs()
        self._last_hash = self._get_index_hash()
        self._inject_auto_refresh()
        
        docs_dir = str(self.docs_dir)
        current_hash_ref = [self._last_hash]
        
        # Keep a reference for the hash endpoint
        server_self = self
        
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=docs_dir, **kwargs)
            
            def do_GET(self):
                if self.path == "/__cortexcode_hash":
                    h = server_self._get_index_hash()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(h.encode())
                    return
                return super().do_GET()
            
            def log_message(self, format, *args):
                pass  # Suppress logs
        
        self._server = http.server.HTTPServer(("0.0.0.0", self.port), Handler)
        self._running = True
        
        # Start polling thread
        poll_thread = threading.Thread(target=self._poll_for_changes, daemon=True)
        poll_thread.start()
        
        # Open browser
        if open_browser:
            import webbrowser
            threading.Timer(0.5, lambda: webbrowser.open(f"http://localhost:{self.port}")).start()
        
        try:
            self._server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            if self._server:
                self._server.shutdown()
    
    def stop(self) -> None:
        """Stop the dashboard server."""
        self._running = False
        if self._server:
            self._server.shutdown()
