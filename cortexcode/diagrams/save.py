import json
from pathlib import Path
from typing import Any

from cortexcode.diagrams.architecture import generate_architecture_diagram
from cortexcode.diagrams.call_graph import generate_call_graph_diagram
from cortexcode.diagrams.class_diagram import generate_class_diagram
from cortexcode.diagrams.dependencies import generate_dependency_graph
from cortexcode.diagrams.entities import generate_entity_diagram
from cortexcode.diagrams.file_tree import generate_file_tree_diagram
from cortexcode.diagrams.imports import generate_import_graph
from cortexcode.diagrams.sequence import generate_sequence_diagram


def generate_all_diagrams(index_data: dict[str, Any], diagram_type: str | None = None) -> dict[str, str]:
    generators = {
        "call_graph": generate_call_graph_diagram,
        "class": generate_class_diagram,
        "sequence": generate_sequence_diagram,
        "architecture": generate_architecture_diagram,
        "imports": generate_import_graph,
        "dependencies": generate_dependency_graph,
        "entities": generate_entity_diagram,
        "file_tree": generate_file_tree_diagram,
    }

    if diagram_type:
        normalized_type = diagram_type.lower()
        if normalized_type not in generators:
            raise ValueError(f"Unknown diagram type: {diagram_type}")
        return {normalized_type: generators[normalized_type](index_data)}

    return {name: generator(index_data) for name, generator in generators.items()}


def save_diagrams(index_path: Path, output_dir: Path, diagram_type: str | None = None) -> None:
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    diagrams = generate_all_diagrams(index_data, diagram_type=diagram_type)

    for name, diagram in diagrams.items():
        (output_dir / f"{name}.mmd").write_text(diagram, encoding="utf-8")

    combined = "# Code Diagrams\n\n"
    combined += "Generated from CortexCode index.\n\n"

    for name, diagram in diagrams.items():
        combined += f"## {name.replace('_', ' ').title()}\n\n"
        combined += f"```mermaid\n{diagram}\n```\n\n"

    (output_dir / "DIAGRAMS.md").write_text(combined, encoding="utf-8")
