from typing import Any

from cortexcode.diagrams.utils import sanitize_id


def generate_dependency_graph(index_data: dict[str, Any]) -> str:
    files = index_data.get("files", {})
    imports = index_data.get("imports", {})

    external_deps = set()
    internal_modules = set()

    for path in files.keys():
        module = path.split("/")[0] if "/" in path else "root"
        internal_modules.add(module)

    for source, targets in imports.items():
        for target in targets:
            if not any(target.startswith(m) for m in internal_modules):
                external_deps.add(target.split(".")[0])

    lines = ["flowchart TD"]
    lines.append("    %% External Dependencies")

    for module in sorted(internal_modules):
        lines.append(f"    {module}[{module}]")

    for dep in sorted(external_deps)[:15]:
        lines.append(f"    ext_{dep}[{dep}]")
        for source, targets in imports.items():
            if dep in targets:
                source_id = sanitize_id(source)
                lines.append(f"    {source_id} --> ext_{dep}")

    return "\n".join(lines)
