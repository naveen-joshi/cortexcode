import re
from difflib import SequenceMatcher
from typing import Any


def fuzzy_search(index: dict, query: str, threshold: float = 0.5, limit: int = 20) -> list[dict[str, Any]]:
    """Fuzzy search for symbols — finds approximate matches.
    
    Uses substring matching, case-insensitive matching, and sequence similarity.
    """
    query_lower = query.lower()
    files = index.get("files", {})
    results = []

    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue
        for sym in file_data.get("symbols", []):
            name = sym.get("name", "")
            name_lower = name.lower()

            if query_lower in name_lower:
                score = 1.0 if query_lower == name_lower else 0.9
            else:
                score = SequenceMatcher(None, query_lower, name_lower).ratio()

                initials = _extract_initials(name)
                if query_lower in initials.lower():
                    score = max(score, 0.75)

                if all(word in name_lower for word in query_lower.split()):
                    score = max(score, 0.8)

            if score >= threshold:
                results.append({
                    "name": name,
                    "type": sym.get("type"),
                    "file": rel_path,
                    "line": sym.get("line"),
                    "params": sym.get("params", []),
                    "doc": sym.get("doc"),
                    "score": round(score, 3),
                })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def regex_search(index: dict, pattern: str, sym_type: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """Search symbols using regex pattern."""
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return [{"error": f"Invalid regex: {e}"}]

    files = index.get("files", {})
    results = []

    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue
        for sym in file_data.get("symbols", []):
            name = sym.get("name", "")
            if regex.search(name):
                if sym_type and sym.get("type") != sym_type:
                    continue
                results.append({
                    "name": name,
                    "type": sym.get("type"),
                    "file": rel_path,
                    "line": sym.get("line"),
                    "params": sym.get("params", []),
                    "doc": sym.get("doc"),
                })

    return results[:limit]


def _extract_initials(name: str) -> str:
    """Extract initials from camelCase/PascalCase/snake_case name."""
    initials = re.findall(r'[A-Z]', name)
    if initials:
        return ''.join(initials)
    parts = name.split('_')
    return ''.join(part[0] for part in parts if part)
