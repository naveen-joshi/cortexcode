"""Data models for the knowledge pack layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Snippet:
    """A code excerpt tied to a specific file and line range."""

    file_path: str
    start_line: int
    end_line: int
    content: str
    language: str = ""
    symbol_name: str | None = None


@dataclass
class Citation:
    """A reference from generated prose back to source code."""

    file_path: str
    line: int
    symbol_name: str | None = None
    snippet: Snippet | None = None


@dataclass
class ConceptEntry:
    """A high-level concept derived from the codebase (auth, payments, etc.)."""

    name: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    related_symbols: list[str] = field(default_factory=list)
    related_files: list[str] = field(default_factory=list)
    related_flows: list[list[str]] = field(default_factory=list)
    snippets: list[Snippet] = field(default_factory=list)


@dataclass
class UsageRecord:
    """Token / cost accounting for a single LLM call."""

    page_id: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached: bool = False
    cost_estimate: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cached": self.cached,
            "cost_estimate": self.cost_estimate,
        }


@dataclass
class PageMeta:
    """Metadata about a single generated documentation page."""

    page_id: str
    title: str
    output_file: str
    citations: list[Citation] = field(default_factory=list)
    usage: UsageRecord | None = None
    status: str = "pending"  # pending | generated | cached | error


@dataclass
class KnowledgePack:
    """The intermediate knowledge representation for a single repo."""

    project_root: str
    project_name: str
    languages: list[str] = field(default_factory=list)
    file_count: int = 0
    symbol_count: int = 0
    call_edge_count: int = 0

    # Structured data derived from the index
    file_summaries: dict[str, dict[str, Any]] = field(default_factory=dict)
    symbol_index: dict[str, dict[str, Any]] = field(default_factory=dict)
    call_graph: dict[str, list[str]] = field(default_factory=dict)
    file_dependencies: dict[str, list[str]] = field(default_factory=dict)
    entry_points: list[dict[str, Any]] = field(default_factory=list)
    frameworks: list[dict[str, Any]] = field(default_factory=list)
    api_routes: list[dict[str, Any]] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)

    # Concept layer
    concepts: list[ConceptEntry] = field(default_factory=list)

    # Snippets keyed by file path
    snippets: dict[str, list[Snippet]] = field(default_factory=dict)

    # Generation metadata
    pages: list[PageMeta] = field(default_factory=list)
    usage_records: list[UsageRecord] = field(default_factory=list)
