from collections import defaultdict
from typing import Any

from cortexcode.diagrams.utils import sanitize_id


def generate_architecture_diagram(index_data: dict[str, Any]) -> str:
    project_profile = index_data.get("project_profile", {})
    layers = project_profile.get("layers", [])
    layer_dependencies = project_profile.get("layer_dependencies", [])
    frameworks = project_profile.get("frameworks", [])

    if layers:
        lines = ["flowchart LR"]
        lines.append("    %% Architecture Overview")
        lines.append("    subgraph layers [Architecture Layers]")

        for layer in layers:
            layer_name = layer.get("name", "unknown")
            layer_id = sanitize_id(f"layer_{layer_name}")
            label = f"{layer_name}<br/>{layer.get('files', 0)} files<br/>{layer.get('symbols', 0)} symbols"
            lines.append(f"        {layer_id}[\"{label}\"]")

        lines.append("    end")

        for dependency in layer_dependencies[:16]:
            source_id = sanitize_id(f"layer_{dependency.get('source', 'unknown')}")
            target_id = sanitize_id(f"layer_{dependency.get('target', 'unknown')}")
            lines.append(f"    {source_id} -->|{dependency.get('count', 0)}| {target_id}")

        if frameworks:
            lines.append("    subgraph tech [Detected Tech]")
            for framework in frameworks[:6]:
                framework_id = sanitize_id(f"fw_{framework.get('name', 'unknown')}")
                lines.append(f"        {framework_id}[\"{framework.get('name', 'unknown')} ({framework.get('count', 0)})\"]")
            lines.append("    end")

        return "\n".join(lines)

    files = index_data.get("files", {})
    components: dict[str, dict[str, Any]] = defaultdict(lambda: {"files": 0, "symbols": 0})

    for path, data in files.items():
        parts = path.split("/")
        component = parts[0] if len(parts) > 1 else "root"
        symbols = data.get("symbols", []) if isinstance(data, dict) else data
        components[component]["files"] += 1
        components[component]["symbols"] += len(symbols)

    lines = ["flowchart TB"]
    lines.append("    %% Architecture Overview")
    lines.append("    subgraph components [Components]")

    for comp, data in sorted(components.items()):
        comp_id = sanitize_id(comp)
        lines.append(f"        {comp_id}[\"{comp}<br/>{data['files']} files<br/>{data['symbols']} symbols\"]")

    lines.append("    end")

    return "\n".join(lines)
