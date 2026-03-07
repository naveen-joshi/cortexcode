"""Snippet extraction — read source excerpts for symbols and line ranges."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cortexcode.knowledge.models import Snippet


def extract_symbol_snippet(
    project_root: str,
    file_path: str,
    symbol: dict[str, Any],
    context_lines: int = 3,
    max_lines: int = 30,
) -> Snippet | None:
    """Extract a code snippet for a symbol with surrounding context."""
    full_path = Path(project_root) / file_path
    if not full_path.is_file():
        return None

    try:
        lines = full_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None

    line = symbol.get("line", 0)
    if line < 1 or line > len(lines):
        return None

    start = max(0, line - 1 - context_lines)
    end = min(len(lines), line - 1 + max_lines)

    content = "\n".join(lines[start:end])
    ext = Path(file_path).suffix.lstrip(".")

    return Snippet(
        file_path=file_path,
        start_line=start + 1,
        end_line=end,
        content=content,
        language=ext,
        symbol_name=symbol.get("name"),
    )


def extract_file_header_snippet(
    project_root: str,
    file_path: str,
    max_lines: int = 40,
) -> Snippet | None:
    """Extract the first N lines of a file as a header snippet."""
    full_path = Path(project_root) / file_path
    if not full_path.is_file():
        return None

    try:
        lines = full_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None

    end = min(len(lines), max_lines)
    content = "\n".join(lines[:end])
    ext = Path(file_path).suffix.lstrip(".")

    return Snippet(
        file_path=file_path,
        start_line=1,
        end_line=end,
        content=content,
        language=ext,
    )


def extract_snippets_for_file(
    project_root: str,
    file_path: str,
    symbols: list[dict[str, Any]],
    max_snippets: int = 5,
) -> list[Snippet]:
    """Extract snippets for the most important symbols in a file."""
    result: list[Snippet] = []

    # Prioritize: classes first, then functions with most calls
    sorted_syms = sorted(
        symbols,
        key=lambda s: (
            0 if s.get("type") == "class" else 1,
            -(len(s.get("calls", []))),
        ),
    )

    for sym in sorted_syms[:max_snippets]:
        snip = extract_symbol_snippet(project_root, file_path, sym)
        if snip:
            result.append(snip)

    return result
