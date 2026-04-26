from pathlib import Path
from typing import Any


def generate_structure_docs(index: dict[str, Any], output_path: Path) -> None:
    files = index.get("files", {})
    profile = index.get("project_profile", {})

    lines = [
        "# Project Structure",
        "",
        "```",
    ]

    for rel_path in sorted(files.keys()):
        lines.append(rel_path)

    lines.append("```")

    # Nx monorepo section
    nx_graph = profile.get("nx_project_graph")
    nx_projects = profile.get("nx_projects")
    if nx_projects:
        lines.append("")
        lines.append("## Nx Workspace")
        lines.append("")
        shell = profile.get("nx_shell_app")
        if shell:
            lines.append(f"**Shell / Root App:** `{shell}`")
            lines.append("")
        lines.append("### Projects")
        lines.append("")
        for name in nx_projects:
            lines.append(f"- `{name}`")
        lines.append("")
        if nx_graph:
            lines.append("### Project Dependencies")
            lines.append("")
            for proj, deps in nx_graph.items():
                if deps:
                    lines.append(f"- `{proj}` → {', '.join(f'`{d}`' for d in deps)}")
                else:
                    lines.append(f"- `{proj}` (no dependencies)")
            lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
