from pathlib import Path
from typing import Any


def generate_api_docs(index: dict, project_root: str | None = None) -> dict[str, Any]:
    """Generate API documentation from function signatures and docstrings."""
    files = index.get("files", {})
    root = Path(project_root) if project_root else None

    modules: list[dict] = []

    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue

        symbols = file_data.get("symbols", [])
        if not symbols:
            continue

        source_lines = None
        if root:
            try:
                source_lines = (root / rel_path).read_text(encoding="utf-8").split("\n")
            except (OSError, UnicodeDecodeError):
                pass

        classes = []
        functions = []

        for sym in symbols:
            name = sym.get("name", "")
            sym_type = sym.get("type", "")
            line = sym.get("line", 0)
            params = sym.get("params", [])
            doc = sym.get("doc", "")

            if not doc and source_lines and line > 0:
                doc = _extract_docstring(source_lines, line - 1)

            entry = {
                "name": name,
                "type": sym_type,
                "line": line,
                "params": params,
                "doc": doc or "",
                "calls": sym.get("calls", []),
                "framework": sym.get("framework"),
            }

            if sym_type == "class":
                classes.append(entry)
            elif sym_type in ("function", "method"):
                functions.append(entry)

        if classes or functions:
            modules.append({
                "file": rel_path,
                "classes": classes,
                "functions": functions,
                "imports": file_data.get("imports", []),
            })

    total_documented = sum(
        1 for module in modules
        for item in module["functions"] + module["classes"]
        if item["doc"]
    )
    total_symbols = sum(
        len(module["functions"]) + len(module["classes"])
        for module in modules
    )

    return {
        "modules": modules,
        "total_modules": len(modules),
        "total_symbols": total_symbols,
        "documented": total_documented,
        "undocumented": total_symbols - total_documented,
        "coverage_pct": round(total_documented / max(total_symbols, 1) * 100, 1),
    }


def _extract_docstring(lines: list[str], start_idx: int) -> str:
    """Extract docstring from the line after a function/class definition."""
    for line_index in range(start_idx + 1, min(start_idx + 5, len(lines))):
        stripped = lines[line_index].strip()
        if not stripped:
            continue

        if stripped.startswith('"""') or stripped.startswith("'''"):
            quote = stripped[:3]
            if stripped.endswith(quote) and len(stripped) > 6:
                return stripped[3:-3].strip()
            doc_lines = [stripped[3:]]
            for doc_line_index in range(line_index + 1, min(line_index + 20, len(lines))):
                line = lines[doc_line_index].strip()
                if line.endswith(quote):
                    doc_lines.append(line[:-3])
                    return "\n".join(doc_lines).strip()
                doc_lines.append(line)
            break

        if stripped.startswith("/**"):
            doc_lines = []
            for doc_line_index in range(line_index, min(line_index + 20, len(lines))):
                line = lines[doc_line_index].strip()
                if line.endswith("*/"):
                    line = line[:-2].strip()
                    if line.startswith("/**"):
                        line = line[3:].strip()
                    elif line.startswith("*"):
                        line = line[1:].strip()
                    if line:
                        doc_lines.append(line)
                    return "\n".join(doc_lines).strip()
                if line.startswith("/**"):
                    line = line[3:].strip()
                elif line.startswith("*"):
                    line = line[1:].strip()
                if line:
                    doc_lines.append(line)
            break

        break

    return ""
