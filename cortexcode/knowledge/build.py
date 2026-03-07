"""Build a KnowledgePack from a CortexCode index."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cortexcode.knowledge.models import KnowledgePack
from cortexcode.knowledge.concepts import build_concept_index
from cortexcode.knowledge.snippets import extract_snippets_for_file


def build_knowledge_pack(
    index_path: Path,
    max_snippets_per_file: int = 5,
) -> KnowledgePack:
    """Build a KnowledgePack from an existing CortexCode index file."""
    index_data = json.loads(Path(index_path).read_text(encoding="utf-8"))
    project_root = index_data.get("project_root", str(index_path.parent.parent))
    project_name = Path(project_root).name

    files = index_data.get("files", {})
    call_graph = index_data.get("call_graph", {})
    file_deps = index_data.get("file_dependencies", {})
    languages = index_data.get("languages", [])
    profile = index_data.get("project_profile", {})

    # Build symbol index: name -> {file, type, line, params, ...}
    symbol_index: dict[str, dict[str, Any]] = {}
    total_symbols = 0
    for file_path, file_data in files.items():
        symbols = file_data.get("symbols", []) if isinstance(file_data, dict) else file_data
        for sym in symbols:
            name = sym.get("name", "")
            if name:
                symbol_index[name] = {**sym, "file": file_path}
                total_symbols += 1

    # File summaries: path -> {symbol_count, types, imports_count, ...}
    file_summaries: dict[str, dict[str, Any]] = {}
    for file_path, file_data in files.items():
        if not isinstance(file_data, dict):
            file_summaries[file_path] = {"symbol_count": len(file_data)}
            continue
        symbols = file_data.get("symbols", [])
        imports = file_data.get("imports", [])
        exports = file_data.get("exports", [])
        routes = file_data.get("api_routes", [])
        entities = file_data.get("entities", [])
        types = set(s.get("type", "") for s in symbols)
        file_summaries[file_path] = {
            "symbol_count": len(symbols),
            "import_count": len(imports),
            "export_count": len(exports),
            "route_count": len(routes),
            "entity_count": len(entities),
            "symbol_types": sorted(types - {""}),
            "symbols": symbols,
            "imports": imports,
            "exports": exports,
            "api_routes": routes,
            "entities": entities,
        }

    # Entry points
    entry_points = profile.get("entry_points", [])

    # Frameworks
    frameworks = profile.get("frameworks", [])

    # Collect all API routes and entities
    all_routes: list[dict[str, Any]] = []
    all_entities: list[dict[str, Any]] = []
    for fp, fs in file_summaries.items():
        for r in fs.get("api_routes", []):
            all_routes.append({**r, "file": fp})
        for e in fs.get("entities", []):
            all_entities.append({**e, "file": fp})

    # Call edge count
    call_edge_count = sum(len(v) for v in call_graph.values())

    # Extract snippets for top files
    snippets_by_file: dict[str, list] = {}
    top_files = sorted(
        file_summaries.items(),
        key=lambda x: -x[1].get("symbol_count", 0),
    )[:50]
    for fp, fs in top_files:
        syms = fs.get("symbols", [])
        if syms:
            file_snips = extract_snippets_for_file(
                project_root, fp, syms, max_snippets=max_snippets_per_file,
            )
            if file_snips:
                snippets_by_file[fp] = file_snips

    # Build concept index
    concepts = build_concept_index(index_data, project_root)

    return KnowledgePack(
        project_root=project_root,
        project_name=project_name,
        languages=languages,
        file_count=len(files),
        symbol_count=total_symbols,
        call_edge_count=call_edge_count,
        file_summaries=file_summaries,
        symbol_index=symbol_index,
        call_graph=call_graph,
        file_dependencies=file_deps,
        entry_points=entry_points,
        frameworks=frameworks,
        api_routes=all_routes,
        entities=all_entities,
        concepts=concepts,
        snippets=snippets_by_file,
    )
