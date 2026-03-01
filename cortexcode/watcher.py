"""File Watcher - Auto-reindex on file changes."""

import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from cortexcode import indexer


class IndexEventHandler(FileSystemEventHandler):
    """Handler that re-indexes files on change."""
    
    def __init__(self, root_path: Path, debounce_seconds: float = 1.0):
        self.root_path = root_path
        self.index_path = root_path / ".cortexcode" / "index.json"
        self.debounce_seconds = debounce_seconds
        self.last_index_time = 0.0
        self.pending_files: set[str] = set()
        self.verbose = False
    
    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if not self._should_index(event.src_path):
            return
        
        self.pending_files.add(event.src_path)
        self._maybe_reindex()
    
    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if not self._should_index(event.src_path):
            return
        
        self.pending_files.add(event.src_path)
        self._maybe_reindex()
    
    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._maybe_reindex()
    
    def _should_index(self, path: str) -> bool:
        """Check if file should be indexed."""
        path_obj = Path(path)
        ext = path_obj.suffix.lower()
        
        if ext not in CodeIndexer.SUPPORTED_EXTENSIONS:
            return False
        
        ignore_patterns = {
            "__pycache__", ".git", ".venv", "venv", "node_modules",
            ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cortexcode"
        }
        
        path_str = str(path_obj)
        return not any(pattern in path_str for pattern in ignore_patterns)
    
    def _maybe_reindex(self) -> None:
        """Debounced reindex."""
        now = time.time()
        
        if now - self.last_index_time < self.debounce_seconds:
            return
        
        if not self.pending_files:
            return
        
        self.pending_files.clear()
        self._reindex()
    
    def _reindex(self) -> None:
        """Perform the reindex."""
        try:
            index_data = indexer.index_directory(self.root_path)
            indexer.save_index(index_data, self.index_path)
            
            if self.verbose:
                print(f"[CortexCode] Re-indexed at {time.strftime('%H:%M:%S')}")
            else:
                print(".", end="", flush=True)
            
            self.last_index_time = time.time()
        except Exception as e:
            print(f"\n[CortexCode] Error re-indexing: {e}")


def start_watcher(root_path: Path, verbose: bool = False) -> None:
    """Start watching a directory for changes.
    
    Args:
        root_path: Directory to watch
        verbose: Print file change events
    """
    root_path = Path(root_path).resolve()
    index_path = root_path / ".cortexcode" / "index.json"
    
    if not index_path.exists():
        print("[CortexCode] No index found. Run 'cortexcode index' first.")
        return
    
    event_handler = IndexEventHandler(root_path)
    event_handler.verbose = verbose
    
    observer = Observer()
    observer.schedule(event_handler, str(root_path), recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()


# Import SUPPORTED_EXTENSIONS from indexer
from cortexcode.indexer import CodeIndexer
