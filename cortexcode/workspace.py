"""Multi-repo workspace support - index and query across multiple repositories."""

import json
from pathlib import Path
from typing import Any

from cortexcode.indexer import CodeIndexer


class Workspace:
    """Manage multiple repositories as a single workspace."""
    
    CONFIG_FILE = ".cortexcode-workspace.json"
    
    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.repos: list[dict[str, Any]] = []
        self.merged_index: dict[str, Any] = {}
    
    def load_config(self) -> bool:
        """Load workspace config from disk."""
        config_path = self.workspace_root / self.CONFIG_FILE
        if not config_path.exists():
            return False
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            self.repos = data.get("repos", [])
            return True
        except (json.JSONDecodeError, OSError):
            return False
    
    def save_config(self) -> None:
        """Save workspace config to disk."""
        config_path = self.workspace_root / self.CONFIG_FILE
        data = {"repos": self.repos}
        config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    def add_repo(self, path: str, alias: str | None = None) -> dict:
        """Add a repository to the workspace."""
        repo_path = Path(path).resolve()
        if not repo_path.is_dir():
            raise ValueError(f"Not a directory: {repo_path}")
        
        # Check not already added
        for r in self.repos:
            if Path(r["path"]).resolve() == repo_path:
                raise ValueError(f"Already in workspace: {repo_path}")
        
        repo = {
            "path": str(repo_path),
            "alias": alias or repo_path.name,
        }
        self.repos.append(repo)
        self.save_config()
        return repo
    
    def remove_repo(self, alias_or_path: str) -> bool:
        """Remove a repository from the workspace."""
        resolved = None
        try:
            resolved = Path(alias_or_path).resolve()
        except Exception:
            pass
        
        for i, r in enumerate(self.repos):
            if r["alias"] == alias_or_path or (resolved and Path(r["path"]).resolve() == resolved):
                self.repos.pop(i)
                self.save_config()
                return True
        return False
    
    def list_repos(self) -> list[dict]:
        """List all repos in workspace."""
        result = []
        for r in self.repos:
            p = Path(r["path"])
            index_path = p / ".cortexcode" / "index.json"
            indexed = index_path.exists()
            result.append({
                "alias": r["alias"],
                "path": r["path"],
                "indexed": indexed,
            })
        return result
    
    def index_all(self, incremental: bool = True) -> dict[str, int]:
        """Index all repos in the workspace. Returns {alias: symbol_count}."""
        results = {}
        for r in self.repos:
            repo_path = Path(r["path"])
            if not repo_path.is_dir():
                results[r["alias"]] = -1
                continue
            
            idx = CodeIndexer()
            index = idx.index_directory(repo_path, incremental=incremental)
            
            output_dir = repo_path / ".cortexcode"
            output_dir.mkdir(exist_ok=True)
            (output_dir / "index.json").write_text(
                json.dumps(index, indent=2, default=str), encoding="utf-8"
            )
            
            results[r["alias"]] = len(index.get("symbols", []))
        
        return results
    
    def get_merged_index(self) -> dict[str, Any]:
        """Load and merge indices from all repos into a single view."""
        merged_files = {}
        merged_call_graph = {}
        merged_symbols = []
        merged_file_deps = {}
        languages = set()
        
        for r in self.repos:
            repo_path = Path(r["path"])
            index_path = repo_path / ".cortexcode" / "index.json"
            if not index_path.exists():
                continue
            
            try:
                index = json.loads(index_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            
            alias = r["alias"]
            
            # Prefix files with repo alias
            for rel_path, file_data in index.get("files", {}).items():
                prefixed = f"{alias}/{rel_path}"
                merged_files[prefixed] = file_data
            
            # Merge call graph
            for caller, callees in index.get("call_graph", {}).items():
                prefixed_caller = f"{alias}:{caller}"
                merged_call_graph[prefixed_caller] = [f"{alias}:{c}" for c in callees]
            
            # Merge symbols
            for sym in index.get("symbols", []):
                sym_copy = dict(sym)
                if "file" in sym_copy:
                    sym_copy["file"] = f"{alias}/{sym_copy['file']}"
                sym_copy["repo"] = alias
                merged_symbols.append(sym_copy)
            
            # Merge file deps
            for f, deps in index.get("file_dependencies", {}).items():
                prefixed_f = f"{alias}/{f}"
                merged_file_deps[prefixed_f] = [f"{alias}/{d}" for d in deps]
            
            languages.update(index.get("languages", []))
        
        self.merged_index = {
            "files": merged_files,
            "call_graph": merged_call_graph,
            "symbols": merged_symbols,
            "file_dependencies": merged_file_deps,
            "languages": sorted(languages),
            "project_root": str(self.workspace_root),
            "repos": [r["alias"] for r in self.repos],
        }
        return self.merged_index
    
    def search_across_repos(self, query: str, max_results: int = 20) -> list[dict]:
        """Search symbols across all repos."""
        if not self.merged_index:
            self.get_merged_index()
        
        query_lower = query.lower()
        results = []
        
        for sym in self.merged_index.get("symbols", []):
            name = sym.get("name", "")
            if query_lower in name.lower():
                results.append(sym)
                if len(results) >= max_results:
                    break
        
        return results
