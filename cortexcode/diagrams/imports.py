from collections import defaultdict
from pathlib import Path
from typing import Any

from cortexcode.diagrams.utils import STYLE_EXTERNAL, STYLE_FUNCTION, sanitize_id


def generate_import_graph(index_data: dict[str, Any], max_depth: int = 20) -> str:
    imports = index_data.get("imports", {})

    lines = ["flowchart LR"]
    lines.append("    %% Import Graph - Package Dependencies")
    lines.append("    direction LR")
    lines.append(STYLE_EXTERNAL)
    lines.append(STYLE_FUNCTION)

    packages: dict[str, list[str]] = defaultdict(list)
    for source, targets in imports.items():
        for target in targets[:5]:
            pkg = target.split(".")[0] if "." in target else target
            packages[pkg].append(target)

    lines.append("    subgraph external [External Packages]")
    for pkg, targets in sorted(packages.items())[:15]:
        if pkg in ["react", "angular", "vue", "lodash", "express", "django", "fastapi"]:
            lines.append(f"        {pkg}[📦 {pkg}]")
    lines.append("    end")

    lines.append("    subgraph internal [Internal Modules]")
    for source, targets in list(imports.items())[:max_depth]:
        source_id = sanitize_id(source)
        lines.append(f"        {source_id}(({Path(source).stem}))")

        for target in targets[:3]:
            target_id = sanitize_id(target)
            pkg = target.split(".")[0] if "." in target else target
            if pkg in ["react", "angular", "vue", "lodash", "express", "django", "fastapi"]:
                lines.append(f"        {source_id} -.-> {pkg}")
            else:
                lines.append(f"        {source_id} --> {target_id}")

    lines.append("    end")

    return "\n".join(lines)
