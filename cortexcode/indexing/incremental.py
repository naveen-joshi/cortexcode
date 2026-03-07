import hashlib
import json
from pathlib import Path
from typing import Any


def load_previous_index_data(root_path: Path, incremental: bool) -> tuple[dict[str, str], dict[str, Any] | None]:
    if not incremental:
        return {}, None

    index_path = root_path / ".cortexcode" / "index.json"
    if not index_path.exists():
        return {}, None

    try:
        old_index = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}, None

    return old_index.get("file_hashes", {}), old_index


def reuse_unchanged_file(
    file_path: Path,
    root_path: Path,
    old_hashes: dict[str, str],
    old_index_data: dict[str, Any] | None,
    file_symbols: dict[str, Any],
    all_symbols: list[dict[str, Any]],
    call_graph: dict[str, list[str]],
) -> bool:
    if not old_hashes or not old_index_data:
        return False

    try:
        current_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
    except OSError:
        return False

    rel_path = str(file_path.relative_to(root_path))
    if old_hashes.get(rel_path) != current_hash:
        return False

    files = old_index_data.get("files", {})
    if rel_path not in files:
        return False

    file_symbols[rel_path] = files[rel_path]
    for sym in files[rel_path].get("symbols", []):
        all_symbols.append(sym)
        name = sym.get("name")
        if not name:
            continue
        if name not in call_graph:
            call_graph[name] = []
        call_graph[name].extend(sym.get("calls", []))
    return True
