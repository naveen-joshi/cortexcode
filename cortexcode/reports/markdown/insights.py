from pathlib import Path
from typing import Any


def generate_insights_docs(index: dict[str, Any], output_path: Path) -> None:
    project_profile = index.get("project_profile", {})
    hotspots = project_profile.get("hotspots", {})
    entry_points = project_profile.get("entry_points", [])
    layer_dependencies = project_profile.get("layer_dependencies", [])

    lines = [
        "# Project Insights",
        "",
        "## Entry Points",
        "",
    ]

    if entry_points:
        for entry_point in entry_points:
            lines.append(
                f"- `{entry_point.get('name', 'unknown')}` in `{entry_point.get('file', 'unknown')}`"
                f" ({entry_point.get('reason', 'detected')})"
            )
    else:
        lines.append("*No entry points inferred.*")

    lines.extend([
        "",
        "## Hotspots by Fan-out",
        "",
    ])

    if hotspots.get("fan_out"):
        for hotspot in hotspots.get("fan_out", []):
            lines.append(f"- `{hotspot.get('name', 'unknown')}` calls {hotspot.get('count', 0)} symbols")
    else:
        lines.append("*No fan-out hotspots detected.*")

    lines.extend([
        "",
        "## Hotspots by Fan-in",
        "",
    ])

    if hotspots.get("fan_in"):
        for hotspot in hotspots.get("fan_in", []):
            lines.append(f"- `{hotspot.get('name', 'unknown')}` is called by {hotspot.get('count', 0)} symbols")
    else:
        lines.append("*No fan-in hotspots detected.*")

    lines.extend([
        "",
        "## Largest Files",
        "",
    ])

    if hotspots.get("top_files"):
        for file_info in hotspots.get("top_files", []):
            lines.append(
                f"- `{file_info.get('file', 'unknown')}` — {file_info.get('symbols', 0)} symbols"
                f" [{file_info.get('role', 'core')}]"
            )
    else:
        lines.append("*No file hotspots detected.*")

    lines.extend([
        "",
        "## Layer Dependencies",
        "",
    ])

    if layer_dependencies:
        for dependency in layer_dependencies[:12]:
            lines.append(
                f"- `{dependency.get('source', 'unknown')}` → `{dependency.get('target', 'unknown')}`"
                f" ({dependency.get('count', 0)} edges)"
            )
    else:
        lines.append("*No cross-layer dependencies inferred.*")

    output_path.write_text("\n".join(lines), encoding="utf-8")
