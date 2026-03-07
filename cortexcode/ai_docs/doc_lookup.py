import json
from pathlib import Path
from typing import Any, Optional


def load_index_data(index_path: Path) -> dict[str, Any]:
    """Load indexed project data from disk."""
    return json.loads(Path(index_path).read_text(encoding="utf-8"))


def find_module_data(index_data: dict[str, Any], module_name: str) -> Optional[dict[str, Any]]:
    """Find indexed data for a module path or prefix."""
    files = index_data.get("files", {})
    for path, data in files.items():
        if module_name in path or path.startswith(module_name):
            return data if isinstance(data, dict) else {"symbols": data}
    return None


def find_symbol_data(index_data: dict[str, Any], symbol_name: str) -> Optional[dict[str, Any]]:
    """Find indexed data for a symbol and attach its file path."""
    for path, data in index_data.get("files", {}).items():
        symbols = data.get("symbols", []) if isinstance(data, dict) else data
        for sym in symbols:
            if sym.get("name") == symbol_name:
                return {**sym, "file": path}
    return None
