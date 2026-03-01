"""Git diff-aware context — show only changed symbols."""

import json
import subprocess
from pathlib import Path
from typing import Any


def get_changed_files(root: Path, ref: str = "HEAD") -> list[str]:
    """Get list of files changed since ref (default: uncommitted changes)."""
    try:
        # Unstaged + staged changes
        result = subprocess.run(
            ["git", "diff", "--name-only", ref],
            capture_output=True, text=True, cwd=str(root)
        )
        files = set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()
        
        # Also include staged changes
        result2 = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=str(root)
        )
        if result2.stdout.strip():
            files.update(result2.stdout.strip().split("\n"))
        
        # Also include untracked files
        result3 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, cwd=str(root)
        )
        if result3.stdout.strip():
            files.update(result3.stdout.strip().split("\n"))
        
        return [f for f in files if f]
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def get_changed_lines(root: Path, file_path: str, ref: str = "HEAD") -> list[tuple[int, int]]:
    """Get ranges of changed lines in a file."""
    try:
        result = subprocess.run(
            ["git", "diff", "-U0", ref, "--", file_path],
            capture_output=True, text=True, cwd=str(root)
        )
        
        ranges = []
        for line in result.stdout.split("\n"):
            if line.startswith("@@"):
                # Parse @@ -old,count +new,count @@
                parts = line.split("+")
                if len(parts) >= 2:
                    new_part = parts[1].split(" ")[0].split(",")
                    start = int(new_part[0])
                    count = int(new_part[1]) if len(new_part) > 1 else 1
                    ranges.append((start, start + count))
        
        return ranges
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        return []


def get_diff_context(index_path: Path, ref: str = "HEAD") -> dict[str, Any]:
    """Get context for only the changed symbols since ref.
    
    Returns symbols that are in files that have been modified,
    with indicators of which ones are in changed line ranges.
    """
    index = json.loads(index_path.read_text(encoding="utf-8"))
    files = index.get("files", {})
    call_graph = index.get("call_graph", {})
    root = Path(index.get("project_root", "."))
    
    changed_files = get_changed_files(root, ref)
    if not changed_files:
        return {
            "ref": ref,
            "changed_files": 0,
            "changed_symbols": [],
            "affected_symbols": [],
        }
    
    changed_symbols = []
    affected_symbol_names = set()
    
    for changed_file in changed_files:
        # Normalize path separators
        norm_file = changed_file.replace("\\", "/")
        
        # Find matching file in index
        file_data = None
        matched_path = None
        for rel_path, data in files.items():
            if rel_path.replace("\\", "/") == norm_file:
                file_data = data
                matched_path = rel_path
                break
        
        if not file_data or not isinstance(file_data, dict):
            continue
        
        symbols = file_data.get("symbols", [])
        changed_ranges = get_changed_lines(root, changed_file, ref)
        
        for sym in symbols:
            sym_line = sym.get("line", 0)
            in_changed_range = any(start <= sym_line <= end for start, end in changed_ranges) if changed_ranges else True
            
            entry = {
                "name": sym.get("name"),
                "type": sym.get("type"),
                "file": matched_path,
                "line": sym_line,
                "changed": in_changed_range,
                "params": sym.get("params", []),
                "calls": sym.get("calls", []),
            }
            
            if sym.get("doc"):
                entry["doc"] = sym["doc"]
            
            changed_symbols.append(entry)
            
            if in_changed_range:
                affected_symbol_names.add(sym.get("name"))
    
    # Find symbols affected by the changes (callers of changed symbols)
    affected_symbols = []
    for name, calls in call_graph.items():
        if any(c in affected_symbol_names for c in calls):
            if name not in affected_symbol_names:
                # Find the file for this symbol
                for rel_path, data in files.items():
                    if not isinstance(data, dict):
                        continue
                    for sym in data.get("symbols", []):
                        if sym.get("name") == name:
                            affected_symbols.append({
                                "name": name,
                                "type": sym.get("type"),
                                "file": rel_path,
                                "line": sym.get("line"),
                                "reason": f"calls changed symbol",
                                "calls_changed": [c for c in calls if c in affected_symbol_names],
                            })
                            break
                    else:
                        continue
                    break
    
    return {
        "ref": ref,
        "changed_files": len(changed_files),
        "changed_symbols": changed_symbols,
        "affected_symbols": affected_symbols[:20],
    }
