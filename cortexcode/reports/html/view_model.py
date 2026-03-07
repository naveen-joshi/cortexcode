from pathlib import Path
from typing import Any


FRAMEWORK_COUNT_KEYS = {
    "react": 0,
    "react-native": 0,
    "expo": 0,
    "angular": 0,
    "nextjs": 0,
    "nestjs": 0,
    "express": 0,
    "flutter": 0,
    "compose": 0,
    "android": 0,
    "swiftui": 0,
    "uikit": 0,
    "ios": 0,
    "spring": 0,
    "fastapi": 0,
    "django": 0,
    "flask": 0,
    "aspnet": 0,
}


def build_dashboard_view_model(index: dict[str, Any]) -> dict[str, Any]:
    files = index.get("files", {})
    call_graph = index.get("call_graph", {})
    file_deps = index.get("file_dependencies", {})
    project_root = index.get("project_root", "")
    last_indexed = index.get("last_indexed", "")
    project_profile = index.get("project_profile", {})

    all_symbols: list[dict[str, Any]] = []
    file_tree: dict[str, Any] = {}
    framework_counts = dict(FRAMEWORK_COUNT_KEYS)
    language_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    all_imports: list[dict[str, Any]] = []
    all_exports: list[dict[str, Any]] = []
    all_api_routes: list[dict[str, Any]] = []
    all_entities: list[dict[str, Any]] = []
    files_with_most_symbols: list[dict[str, Any]] = []
    profile_frameworks = project_profile.get("frameworks", [])
    profile_layers = project_profile.get("layers", [])
    profile_entry_points = project_profile.get("entry_points", [])
    profile_recommendations = project_profile.get("recommendations", {})

    for rel_path, file_data in files.items():
        symbols = file_data.get("symbols", []) if isinstance(file_data, dict) else file_data
        imports = file_data.get("imports", []) if isinstance(file_data, dict) else []
        exports = file_data.get("exports", []) if isinstance(file_data, dict) else []
        api_routes = file_data.get("api_routes", []) if isinstance(file_data, dict) else []
        entities = file_data.get("entities", []) if isinstance(file_data, dict) else []

        ext = Path(rel_path).suffix
        language_counts[ext] = language_counts.get(ext, 0) + 1

        parts = rel_path.replace("\\", "/").split("/")
        current = file_tree
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        if parts[-1] not in current:
            current[parts[-1]] = symbols

        all_imports.extend([{"file": rel_path, **imp} for imp in imports])
        all_exports.extend([{"file": rel_path, **exp} for exp in exports])
        all_api_routes.extend([{"file": rel_path, **route} for route in api_routes])
        all_entities.extend([{"file": rel_path, **ent} for ent in entities])

        files_with_most_symbols.append({"file": rel_path, "count": len(symbols)})

        for sym in symbols:
            sym_copy = dict(sym) if isinstance(sym, dict) else {"name": str(sym)}
            sym_copy["file"] = rel_path
            all_symbols.append(sym_copy)
            sym_type = sym_copy.get("type", "unknown")
            type_counts[sym_type] = type_counts.get(sym_type, 0) + 1

            fw = sym_copy.get("framework")
            if fw:
                for key in framework_counts:
                    if key in fw:
                        framework_counts[key] += 1
                        break

    files_with_most_symbols.sort(key=lambda x: x["count"], reverse=True)

    non_empty_calls = sum(1 for v in call_graph.values() if v)
    total_call_edges = sum(len(v) for v in call_graph.values() if v)
    top_callers = sorted(
        [(k, len(v)) for k, v in call_graph.items() if v],
        key=lambda x: x[1], reverse=True,
    )[:10]

    project_name = Path(project_root).name

    return {
        "files": files,
        "call_graph": call_graph,
        "file_deps": file_deps,
        "project_root": project_root,
        "last_indexed": last_indexed,
        "project_profile": project_profile,
        "all_symbols": all_symbols,
        "file_tree": file_tree,
        "framework_counts": framework_counts,
        "language_counts": language_counts,
        "type_counts": type_counts,
        "all_imports": all_imports,
        "all_exports": all_exports,
        "all_api_routes": all_api_routes,
        "all_entities": all_entities,
        "files_with_most_symbols": files_with_most_symbols,
        "profile_frameworks": profile_frameworks,
        "profile_layers": profile_layers,
        "profile_entry_points": profile_entry_points,
        "profile_recommendations": profile_recommendations,
        "non_empty_calls": non_empty_calls,
        "total_call_edges": total_call_edges,
        "top_callers": top_callers,
        "project_name": project_name,
    }
