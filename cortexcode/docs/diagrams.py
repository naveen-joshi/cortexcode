"""Diagram generator - Create Mermaid diagrams from index data without LLM."""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

from cortexcode.diagrams.architecture import generate_architecture_diagram as generate_architecture_renderer
from cortexcode.diagrams.call_graph import generate_call_graph_diagram as generate_call_graph_renderer
from cortexcode.diagrams.class_diagram import generate_class_diagram as generate_class_renderer
from cortexcode.diagrams.dependencies import generate_dependency_graph as generate_dependency_renderer
from cortexcode.diagrams.directory_tree import generate_directory_tree as generate_directory_tree_renderer
from cortexcode.diagrams.entities import generate_entity_diagram as generate_entity_renderer
from cortexcode.diagrams.file_tree import generate_file_tree_diagram as generate_file_tree_renderer
from cortexcode.diagrams.imports import generate_import_graph as generate_import_renderer
from cortexcode.diagrams.save import generate_all_diagrams as generate_all_diagrams_renderer
from cortexcode.diagrams.save import save_diagrams as save_diagrams_renderer
from cortexcode.diagrams.sequence import generate_sequence_diagram as generate_sequence_renderer
from cortexcode.diagrams.state import generate_state_diagram as generate_state_renderer


# Styling constants
STYLE_CLASS = '    classDef class fill:#f9f,stroke:#333,stroke-width:2px'
STYLE_FUNCTION = '    classDef function fill:#bbf,stroke:#333,stroke-width:2px'
STYLE_INTERFACE = '    classDef interface fill:#bfb,stroke:#333,stroke-width:2px'
STYLE_EXTERNAL = '    classDef external fill:#eee,stroke:#999,stroke-width:1px,dash:5,5'


def generate_call_graph_diagram(index_data: Dict[str, Any], max_nodes: int = 30) -> str:
    """Generate Mermaid flowchart from call graph with styling."""
    return generate_call_graph_renderer(index_data, max_nodes=max_nodes)


def generate_class_diagram(index_data: Dict[str, Any]) -> str:
    """Generate Mermaid class diagram from symbols with relationships."""
    return generate_class_renderer(index_data)


def generate_sequence_diagram(index_data: Dict[str, Any], entry_point: str = "main") -> str:
    """Generate Mermaid sequence diagram from call graph."""
    return generate_sequence_renderer(index_data, entry_point=entry_point)


def generate_directory_tree(index_data: Dict[str, Any]) -> str:
    """Generate Mermaid mindmap from directory structure."""
    return generate_directory_tree_renderer(index_data)


def generate_import_graph(index_data: Dict[str, Any], max_depth: int = 20) -> str:
    """Generate Mermaid flowchart showing import relationships with package grouping."""
    return generate_import_renderer(index_data, max_depth=max_depth)


def generate_architecture_diagram(index_data: Dict[str, Any]) -> str:
    """Generate architecture overview with components."""
    return generate_architecture_renderer(index_data)


def generate_state_diagram(index_data: Dict[str, Any]) -> str:
    """Generate state diagram from possible state transitions (inferred from function patterns)."""
    return generate_state_renderer(index_data)


def generate_dependency_graph(index_data: Dict[str, Any]) -> str:
    """Generate dependency graph between modules."""
    return generate_dependency_renderer(index_data)


def generate_entity_diagram(index_data: Dict[str, Any]) -> str:
    """Generate ER diagram for database entities/models."""
    return generate_entity_renderer(index_data)


def generate_file_tree_diagram(index_data: Dict[str, Any], max_depth: int = 3) -> str:
    """Generate file tree diagram."""
    return generate_file_tree_renderer(index_data, max_depth=max_depth)


def _sanitize_id(name: str) -> str:
    """Sanitize name for Mermaid diagram."""
    # Replace special chars with underscores
    import re
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Ensure it starts with a letter
    if sanitized and sanitized[0].isdigit():
        sanitized = "n" + sanitized
    return sanitized[:50]  # Limit length


def _build_callers(call_graph: Dict[str, List[str]]) -> Dict[str, List[str]]:
    callers: Dict[str, List[str]] = defaultdict(list)
    for caller, callees in call_graph.items():
        for callee in callees:
            callers[callee].append(caller)
    return callers


def generate_all_diagrams(index_data: Dict[str, Any], diagram_type: Optional[str] = None) -> Dict[str, str]:
    """Generate all available diagrams."""
    return generate_all_diagrams_renderer(index_data, diagram_type=diagram_type)


def save_diagrams(index_path: Path, output_dir: Path, diagram_type: Optional[str] = None) -> None:
    """Generate and save all diagrams to files."""
    save_diagrams_renderer(index_path, output_dir, diagram_type=diagram_type)
