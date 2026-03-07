from collections import defaultdict
from pathlib import Path
from typing import Any


def generate_readme(index: dict[str, Any], output_path: Path) -> None:
    files = index.get("files", {})
    call_graph = index.get("call_graph", {})
    project_profile = index.get("project_profile", {})
    frameworks = project_profile.get("frameworks", [])
    entry_points = project_profile.get("entry_points", [])

    directories = defaultdict(list)
    for rel_path in files.keys():
        parts = Path(rel_path).parts
        if len(parts) > 1:
            directories[parts[0]].append(rel_path)

    lines = [
        "# Project Documentation",
        "",
        "## Overview",
        "",
        f"**Project Root:** `{index.get('project_root', 'N/A')}`",
        f"**Last Indexed:** {index.get('last_indexed', 'N/A')}",
        "",
        "## Key Modules",
        "",
    ]

    for dir_name, dir_files in sorted(directories.items()):
        lines.append(f"- `{dir_name}/` — {len(dir_files)} files")

    lines.extend([
        "",
        "## Detected Tech",
        "",
    ])

    if frameworks:
        for framework in frameworks[:8]:
            lines.append(f"- `{framework.get('name', 'unknown')}` — {framework.get('count', 0)} symbols")
    else:
        lines.append("  (No framework signatures detected)")

    lines.extend([
        "",
        "## Entry Points",
        "",
    ])

    if entry_points:
        for entry_point in entry_points[:8]:
            lines.append(
                f"- `{entry_point.get('name', 'unknown')}` in `{entry_point.get('file', 'unknown')}`"
                f" ({entry_point.get('reason', 'detected')})"
            )
    else:
        for rel_path in files.keys():
            if Path(rel_path).name in ("main.py", "app.py", "server.py", "cli.py", "__main__.py"):
                lines.append(f"- `{rel_path}`")

    if not entry_points and not any(Path(p).name in ("main.py", "app.py", "server.py", "cli.py", "__main__.py") for p in files.keys()):
        lines.append("  (No obvious entry points found)")

    lines.extend([
        "",
        "## Symbol Count",
        "",
        f"- **Files:** {len(files)}",
        f"- **Symbols:** {len(call_graph)}",
    ])

    output_path.write_text("\n".join(lines), encoding="utf-8")
