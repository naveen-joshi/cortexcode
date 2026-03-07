import hashlib
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


def detect_duplicates(index: dict, project_root: str | None = None, min_lines: int = 5) -> list[dict[str, Any]]:
    """Find duplicate or very similar code blocks.
    
    Compares function bodies by normalizing whitespace and variable names,
    then computing similarity scores.
    """
    files = index.get("files", {})
    root = Path(project_root) if project_root else None

    functions: list[dict] = []
    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue

        source_lines = None
        if root:
            try:
                source_lines = (root / rel_path).read_text(encoding="utf-8").split("\n")
            except (OSError, UnicodeDecodeError):
                continue

        if not source_lines:
            continue

        for sym in file_data.get("symbols", []):
            if sym.get("type") not in ("function", "method"):
                continue

            line = sym.get("line", 0)
            if line <= 0:
                continue

            body = _extract_function_body(source_lines, line - 1)
            if len(body.split("\n")) < min_lines:
                continue

            normalized = _normalize_code(body)
            functions.append({
                "name": sym.get("name", ""),
                "file": rel_path,
                "line": line,
                "body": body,
                "normalized": normalized,
                "hash": hashlib.md5(normalized.encode()).hexdigest(),
            })

    hash_groups: dict[str, list] = {}
    for func in functions:
        func_hash = func["hash"]
        if func_hash not in hash_groups:
            hash_groups[func_hash] = []
        hash_groups[func_hash].append(func)

    duplicates = []
    seen_pairs = set()

    for func_hash, group in hash_groups.items():
        if len(group) > 1:
            duplicates.append({
                "type": "exact",
                "similarity": 1.0,
                "functions": [
                    {"name": func["name"], "file": func["file"], "line": func["line"]}
                    for func in group
                ],
                "lines": len(group[0]["body"].split("\n")),
            })
            for func in group:
                seen_pairs.add((func["file"], func["line"]))

    for index_position, first_func in enumerate(functions):
        if (first_func["file"], first_func["line"]) in seen_pairs:
            continue
        for second_func in functions[index_position + 1:]:
            if (second_func["file"], second_func["line"]) in seen_pairs:
                continue
            if first_func["hash"] == second_func["hash"]:
                continue

            similarity = SequenceMatcher(None, first_func["normalized"], second_func["normalized"]).ratio()
            if similarity > 0.8:
                duplicates.append({
                    "type": "near",
                    "similarity": round(similarity, 3),
                    "functions": [
                        {"name": first_func["name"], "file": first_func["file"], "line": first_func["line"]},
                        {"name": second_func["name"], "file": second_func["file"], "line": second_func["line"]},
                    ],
                    "lines": max(
                        len(first_func["body"].split("\n")),
                        len(second_func["body"].split("\n")),
                    ),
                })

    duplicates.sort(key=lambda x: x["similarity"], reverse=True)
    return duplicates


def _extract_function_body(lines: list[str], start_idx: int) -> str:
    """Extract function body from source lines."""
    if start_idx >= len(lines):
        return ""

    start_line = lines[start_idx]
    start_indent = len(start_line) - len(start_line.lstrip())
    indent_based = "def " in start_line or start_line.strip().endswith(":")

    body = [lines[start_idx]]
    brace_depth = 0

    for line_index in range(start_idx + 1, min(start_idx + 300, len(lines))):
        line = lines[line_index]
        stripped = line.strip()

        if not stripped:
            body.append(line)
            continue

        if indent_based:
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= start_indent and stripped and not stripped.startswith((")", "]", "}")):
                break
        else:
            brace_depth += stripped.count("{") - stripped.count("}")
            if brace_depth <= 0 and len(body) > 1:
                body.append(line)
                break

        body.append(line)

    return "\n".join(body)


def _normalize_code(code: str) -> str:
    """Normalize code for comparison — remove comments, normalize whitespace, replace identifiers."""
    lines = []
    for line in code.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        stripped = re.sub(r'#.*$', '', stripped)
        stripped = re.sub(r'//.*$', '', stripped)
        stripped = stripped.strip()
        if stripped:
            lines.append(stripped)

    result = "\n".join(lines)
    result = re.sub(r'"[^"]*"', '"STR"', result)
    result = re.sub(r"'[^']*'", "'STR'", result)
    result = re.sub(r'\b\d+\b', 'NUM', result)
    return result
