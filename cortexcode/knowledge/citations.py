"""Citation helpers — link generated prose back to source code."""

from __future__ import annotations

from typing import Any

from cortexcode.knowledge.models import Citation, Snippet


def citation_for_symbol(
    file_path: str,
    symbol: dict[str, Any],
    snippet: Snippet | None = None,
) -> Citation:
    """Create a citation for a symbol definition."""
    return Citation(
        file_path=file_path,
        line=symbol.get("line", 0),
        symbol_name=symbol.get("name"),
        snippet=snippet,
    )


def citation_for_file(file_path: str, line: int = 1) -> Citation:
    """Create a citation for a file location."""
    return Citation(file_path=file_path, line=line)


def format_citation_markdown(citation: Citation) -> str:
    """Format a citation as a readable markdown reference."""
    parts = [f"`{citation.file_path}`"]
    if citation.line > 0:
        parts.append(f"line {citation.line}")
    if citation.symbol_name:
        parts.append(f"(`{citation.symbol_name}`)")
    return " ".join(parts)


def format_citations_section(citations: list[Citation]) -> str:
    """Format a list of citations as a markdown references section."""
    if not citations:
        return ""
    lines = ["", "---", "**References:**", ""]
    for c in citations:
        lines.append(f"- {format_citation_markdown(c)}")
    return "\n".join(lines)
