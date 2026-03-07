import re
from pathlib import Path
from typing import Any


def compute_complexity(index: dict, project_root: str | None = None) -> list[dict[str, Any]]:
    """Compute complexity metrics for all functions/methods.

    Metrics:
    - lines: approximate line count of the function body
    - params: number of parameters
    - calls: number of outgoing calls
    - cyclomatic: estimated cyclomatic complexity (branch count + 1)
    - nesting: max nesting depth estimate
    """
    files = index.get("files", {})
    results: list[dict[str, Any]] = []
    root = Path(project_root) if project_root else None

    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue

        symbols = file_data.get("symbols", [])
        source_lines: list[str] | None = None
        if root:
            try:
                source_lines = (root / rel_path).read_text(encoding="utf-8").split("\n")
            except (OSError, UnicodeDecodeError):
                pass

        for sym in symbols:
            if sym.get("type") not in ("function", "method"):
                continue

            line = sym.get("line", 0)
            metrics = {
                "name": sym.get("name", ""),
                "type": sym.get("type"),
                "file": rel_path,
                "line": line,
                "params_count": len(sym.get("params", [])),
                "calls_count": len(sym.get("calls", [])),
            }

            if source_lines and line > 0:
                body_lines, cyclomatic, nesting = _analyze_function_body(source_lines, line - 1)
                metrics["lines"] = body_lines
                metrics["cyclomatic"] = cyclomatic
                metrics["max_nesting"] = nesting

            score = _complexity_score(metrics)
            metrics["score"] = score
            metrics["rating"] = "low" if score < 20 else "medium" if score < 50 else "high" if score < 80 else "critical"
            results.append(metrics)

    results.sort(key=lambda item: item.get("score", 0), reverse=True)
    return results


def _analyze_function_body(lines: list[str], start_idx: int) -> tuple[int, int, int]:
    """Analyze function body for line count, cyclomatic complexity, and nesting depth.

    Returns: (line_count, cyclomatic_complexity, max_nesting_depth)
    """
    branch_re = re.compile(r'\b(if|elif|else if|for|while|catch|except|case|&&|\|\||and |or |when)\b')

    start_line = lines[start_idx] if start_idx < len(lines) else ""
    start_indent = len(start_line) - len(start_line.lstrip())

    body_lines = 0
    branch_count = 0
    max_nesting = 0
    brace_depth = 0
    indent_based = "def " in start_line or start_line.strip().endswith(":")

    for line_index in range(start_idx + 1, min(start_idx + 500, len(lines))):
        line = lines[line_index]
        stripped = line.strip()

        if not stripped or stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
            continue

        if indent_based:
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= start_indent and stripped and not stripped.startswith((")", "]", "}")):
                break
            nesting = (current_indent - start_indent) // 4
        else:
            brace_depth += stripped.count("{") - stripped.count("}")
            if brace_depth <= 0 and body_lines > 0:
                break
            nesting = brace_depth

        body_lines += 1
        max_nesting = max(max_nesting, nesting)
        branch_count += len(branch_re.findall(stripped))

    cyclomatic = branch_count + 1
    return body_lines, cyclomatic, max_nesting


def _complexity_score(metrics: dict) -> int:
    """Compute a 0-100 complexity score from metrics."""
    score = 0.0

    body_lines = metrics.get("lines", 0)
    if body_lines > 100:
        score += 30
    elif body_lines > 50:
        score += 20
    elif body_lines > 25:
        score += 10
    elif body_lines > 10:
        score += 5

    cyclomatic = metrics.get("cyclomatic", 1)
    if cyclomatic > 20:
        score += 30
    elif cyclomatic > 10:
        score += 20
    elif cyclomatic > 5:
        score += 10
    elif cyclomatic > 3:
        score += 5

    nesting = metrics.get("max_nesting", 0)
    if nesting > 5:
        score += 20
    elif nesting > 3:
        score += 10
    elif nesting > 2:
        score += 5

    params = metrics.get("params_count", 0)
    if params > 7:
        score += 10
    elif params > 4:
        score += 5

    calls = metrics.get("calls_count", 0)
    if calls > 15:
        score += 10
    elif calls > 8:
        score += 5

    return min(100, int(score))
