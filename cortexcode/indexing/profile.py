from pathlib import Path
from typing import Any


FRONTEND_FRAMEWORKS = {"react", "react-native", "nextjs", "angular", "expo", "flutter", "swiftui", "uikit", "remix"}


def build_callers(call_graph: dict[str, list[str]]) -> dict[str, list[str]]:
    callers: dict[str, list[str]] = {}
    for caller, callees in call_graph.items():
        for callee in set(callees):
            callers.setdefault(callee, []).append(caller)
    return callers


def normalize_framework(framework: str | None) -> str | None:
    if not framework:
        return None

    normalized = framework.lower()
    framework_groups = [
        ("react-native", "react-native"),
        ("nextjs", "nextjs"),
        ("nestjs", "nestjs"),
        ("fastapi", "fastapi"),
        ("django", "django"),
        ("flask", "flask"),
        ("spring", "spring"),
        ("aspnet", "aspnet"),
        ("angular", "angular"),
        ("react", "react"),
        ("expo", "expo"),
        ("flutter", "flutter"),
        ("swiftui", "swiftui"),
        ("uikit", "uikit"),
        ("express", "express"),
        ("remix", "remix"),
    ]
    for needle, label in framework_groups:
        if needle in normalized:
            return label
    return normalized


def infer_file_role(rel_path: str, file_data: dict[str, Any]) -> str:
    normalized_path = rel_path.replace("\\", "/").lower()
    file_name = Path(normalized_path).name
    symbols = file_data.get("symbols", [])
    routes = file_data.get("api_routes", [])
    entities = file_data.get("entities", [])
    frameworks = {
        normalize_framework(sym.get("framework"))
        for sym in symbols
        if isinstance(sym, dict) and sym.get("framework")
    }

    if file_name in ("cli.py", "manage.py") or any(segment in normalized_path for segment in ("/cli/", "/commands/")):
        return "cli"
    if routes or any(segment in normalized_path for segment in ("/api/", "/routes/", "/route/", "/controllers/", "/handlers/", "/endpoints/")):
        return "api"
    if entities or any(segment in normalized_path for segment in ("/models/", "/model/", "/schemas/", "/schema/", "/entities/", "/entity/", "/db/", "/database/", "/migrations/", "/repositories/")):
        return "data"
    if frameworks & FRONTEND_FRAMEWORKS or any(segment in normalized_path for segment in ("/components/", "/pages/", "/screens/", "/views/", "/ui/", "/widgets/")):
        return "ui"
    if any(segment in normalized_path for segment in ("/services/", "/service/", "/usecases/", "/use-cases/", "/stores/", "/state/", "/domain/")):
        return "services"
    if any(segment in normalized_path for segment in ("/config/", "/middleware/", "/middlewares/", "/auth/", "/infra/", "/platform/", "/plugins/")):
        return "infra"
    return "core"


def infer_file_entry_points(
    rel_path: str,
    file_data: dict[str, Any],
    callers: dict[str, list[str]],
) -> list[dict[str, Any]]:
    normalized_path = rel_path.replace("\\", "/").lower()
    file_name = Path(normalized_path).name
    symbols = file_data.get("symbols", [])
    routes = file_data.get("api_routes", [])
    entry_points: list[dict[str, Any]] = []

    if file_name in ("main.py", "app.py", "server.py", "cli.py", "__main__.py", "manage.py", "main.ts", "main.js", "index.ts", "index.js"):
        for sym in symbols:
            if sym.get("type") in ("function", "class") and not sym.get("class"):
                entry_points.append({"name": sym.get("name"), "file": rel_path, "reason": "entry_file"})
                if len(entry_points) >= 3:
                    break

    for route in routes[:5]:
        method = str(route.get("method", "")).upper().strip()
        route_path = str(route.get("path", "")).strip()
        label = f"{method} {route_path}".strip()
        if label:
            entry_points.append({"name": label, "file": rel_path, "reason": "api_route"})

    for sym in symbols:
        if sym.get("type") == "function" and not sym.get("class") and sym.get("name") not in callers:
            entry_points.append({"name": sym.get("name"), "file": rel_path, "reason": "top_level"})
            if len(entry_points) >= 8:
                break

    return [entry for entry in entry_points if entry.get("name")]


def build_recommendations(
    frameworks: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    layers: list[dict[str, Any]],
) -> dict[str, list[str]]:
    report_types = ["overview", "tech", "hotspots"]
    diagram_types = ["architecture", "call_graph", "dependencies"]
    layer_names = {layer.get("name") for layer in layers}
    framework_names = {framework.get("name") for framework in frameworks}

    if routes:
        report_types.append("routes")
        diagram_types.append("sequence")
    if entities:
        report_types.append("entities")
        diagram_types.append("entities")
    if "ui" in layer_names or framework_names & FRONTEND_FRAMEWORKS:
        report_types.append("frontend")
    if "cli" in layer_names:
        report_types.append("cli")
    if framework_names:
        diagram_types.append("imports")

    return {
        "reports": list(dict.fromkeys(report_types)),
        "diagrams": list(dict.fromkeys(diagram_types)),
    }


def build_project_profile(
    file_symbols: dict[str, Any],
    call_graph: dict[str, list[str]],
    file_deps: dict[str, list[str]],
) -> dict[str, Any]:
    framework_counts: dict[str, int] = {}
    symbol_type_counts: dict[str, int] = {}
    layer_stats: dict[str, dict[str, int]] = {}
    entry_points: list[dict[str, Any]] = []
    route_samples: list[dict[str, Any]] = []
    entity_samples: list[dict[str, Any]] = []
    top_files: list[dict[str, Any]] = []
    role_by_file: dict[str, str] = {}
    callers = build_callers(call_graph)

    for rel_path, file_data in file_symbols.items():
        if not isinstance(file_data, dict):
            continue

        symbols = file_data.get("symbols", [])
        api_routes = file_data.get("api_routes", [])
        entities = file_data.get("entities", [])
        role = infer_file_role(rel_path, file_data)
        role_by_file[rel_path] = role

        bucket = layer_stats.setdefault(role, {"files": 0, "symbols": 0, "routes": 0, "entities": 0})
        bucket["files"] += 1
        bucket["symbols"] += len(symbols)
        bucket["routes"] += len(api_routes)
        bucket["entities"] += len(entities)

        top_files.append({
            "file": rel_path,
            "symbols": len(symbols),
            "routes": len(api_routes),
            "entities": len(entities),
            "role": role,
        })

        for route in api_routes:
            route_samples.append({"file": rel_path, **route})

        for entity in entities:
            entity_samples.append({"file": rel_path, **entity})

        for sym in symbols:
            sym_type = sym.get("type")
            if sym_type:
                symbol_type_counts[sym_type] = symbol_type_counts.get(sym_type, 0) + 1

            normalized_framework = normalize_framework(sym.get("framework"))
            if normalized_framework:
                framework_counts[normalized_framework] = framework_counts.get(normalized_framework, 0) + 1

        entry_points.extend(infer_file_entry_points(rel_path, file_data, callers))

    layer_dependencies: dict[tuple[str, str], int] = {}
    for source_file, target_files in file_deps.items():
        source_role = role_by_file.get(source_file, "core")
        for target_file in target_files:
            target_role = role_by_file.get(target_file, "core")
            if source_role == target_role:
                continue
            key = (source_role, target_role)
            layer_dependencies[key] = layer_dependencies.get(key, 0) + 1

    fan_out = sorted(
        (
            {"name": name, "count": len(set(callees))}
            for name, callees in call_graph.items()
            if callees
        ),
        key=lambda item: item["count"],
        reverse=True,
    )[:10]

    fan_in = sorted(
        (
            {"name": name, "count": len(set(symbol_callers))}
            for name, symbol_callers in callers.items()
            if symbol_callers
        ),
        key=lambda item: item["count"],
        reverse=True,
    )[:10]

    deduped_entry_points = []
    seen_entry_points = set()
    for entry_point in entry_points:
        key = (entry_point.get("name"), entry_point.get("file"), entry_point.get("reason"))
        if key in seen_entry_points:
            continue
        seen_entry_points.add(key)
        deduped_entry_points.append(entry_point)
        if len(deduped_entry_points) >= 12:
            break

    layers = [
        {"name": layer_name, **stats}
        for layer_name, stats in sorted(layer_stats.items(), key=lambda item: (-item[1]["files"], item[0]))
    ]

    frameworks = [
        {"name": framework_name, "count": count}
        for framework_name, count in sorted(framework_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    layer_edges = [
        {"source": source, "target": target, "count": count}
        for (source, target), count in sorted(layer_dependencies.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))
    ]

    top_files.sort(key=lambda item: (-item["symbols"], item["file"]))

    recommendations = build_recommendations(frameworks, route_samples, entity_samples, layers)

    return {
        "frameworks": frameworks,
        "symbol_types": [
            {"name": symbol_type, "count": count}
            for symbol_type, count in sorted(symbol_type_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "layers": layers,
        "layer_dependencies": layer_edges,
        "entry_points": deduped_entry_points,
        "hotspots": {
            "fan_out": fan_out,
            "fan_in": fan_in,
            "top_files": top_files[:10],
        },
        "route_count": len(route_samples),
        "entity_count": len(entity_samples),
        "route_samples": route_samples[:20],
        "entity_samples": entity_samples[:20],
        "recommendations": recommendations,
    }
