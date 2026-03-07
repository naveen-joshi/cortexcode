from pathlib import Path
from typing import Any


def generate_tech_docs(index: dict[str, Any], output_path: Path) -> None:
    project_profile = index.get("project_profile", {})
    frameworks = project_profile.get("frameworks", [])
    layers = project_profile.get("layers", [])
    recommendations = project_profile.get("recommendations", {})
    route_samples = project_profile.get("route_samples", [])
    entity_samples = project_profile.get("entity_samples", [])

    lines = [
        "# Technology Profile",
        "",
        f"**Project Root:** `{index.get('project_root', 'N/A')}`",
        f"**Languages:** {', '.join(index.get('languages', [])) or 'N/A'}",
        "",
        "## Frameworks",
        "",
    ]

    if frameworks:
        for framework in frameworks:
            lines.append(f"- `{framework.get('name', 'unknown')}` — {framework.get('count', 0)} symbols")
    else:
        lines.append("*No framework signatures detected.*")

    lines.extend([
        "",
        "## Architecture Layers",
        "",
    ])

    if layers:
        for layer in layers:
            extras = []
            if layer.get("routes"):
                extras.append(f"{layer.get('routes')} routes")
            if layer.get("entities"):
                extras.append(f"{layer.get('entities')} entities")
            suffix = f" ({', '.join(extras)})" if extras else ""
            lines.append(
                f"- `{layer.get('name', 'unknown')}` — {layer.get('files', 0)} files, {layer.get('symbols', 0)} symbols{suffix}"
            )
    else:
        lines.append("*No architecture layers inferred.*")

    lines.extend([
        "",
        "## Runtime Surface",
        "",
        f"- **API routes:** {project_profile.get('route_count', 0)}",
        f"- **Entities:** {project_profile.get('entity_count', 0)}",
        "",
        "## Recommended Reports",
        "",
    ])

    for report_name in recommendations.get("reports", []):
        lines.append(f"- `{report_name}`")

    lines.extend([
        "",
        "## Recommended Diagrams",
        "",
    ])

    for diagram_name in recommendations.get("diagrams", []):
        lines.append(f"- `{diagram_name}`")

    if route_samples:
        lines.extend([
            "",
            "## Route Samples",
            "",
        ])
        for route in route_samples[:10]:
            lines.append(
                f"- `{route.get('method', 'UNKNOWN')} {route.get('path', '/')}` in `{route.get('file', 'unknown')}`"
            )

    if entity_samples:
        lines.extend([
            "",
            "## Entity Samples",
            "",
        ])
        for entity in entity_samples[:10]:
            field_count = len(entity.get("fields", [])) if isinstance(entity.get("fields"), list) else 0
            lines.append(
                f"- `{entity.get('name', 'unknown')}` ({entity.get('type', 'unknown')}) in `{entity.get('file', 'unknown')}` — {field_count} fields"
            )

    output_path.write_text("\n".join(lines), encoding="utf-8")
