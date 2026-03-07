from typing import Any

from cortexcode.diagrams.utils import STYLE_CLASS, STYLE_EXTERNAL, STYLE_FUNCTION, build_callers, sanitize_id


def generate_call_graph_diagram(index_data: dict[str, Any], max_nodes: int = 30) -> str:
    call_graph = index_data.get("call_graph", {})
    project_profile = index_data.get("project_profile", {})

    lines = ["flowchart TD"]
    lines.append("    %% Call Graph")
    lines.append("    subgraph entry [Entry Points]")
    lines.append(STYLE_CLASS)
    lines.append(STYLE_FUNCTION)
    lines.append(STYLE_EXTERNAL)

    callers = build_callers(call_graph)
    entry_points = [
        entry_point.get("name")
        for entry_point in project_profile.get("entry_points", [])
        if entry_point.get("name") in call_graph
    ]
    if not entry_points:
        entry_points = [f for f in call_graph.keys() if f not in callers]

    for ep in entry_points[:5]:
        lines.append(f"    {sanitize_id(ep)}[💡 {ep}]")

    lines.append("    end")
    lines.append("")
    lines.append("    subgraph main [Main Flow]")

    selected_nodes = []
    queue = list(dict.fromkeys(entry_points[:5]))
    visited = set()
    while queue and len(selected_nodes) < max_nodes:
        caller = queue.pop(0)
        if caller in visited or caller not in call_graph:
            continue
        visited.add(caller)
        selected_nodes.append(caller)
        for callee in call_graph.get(caller, [])[:5]:
            if callee in call_graph and callee not in visited:
                queue.append(callee)

    if not selected_nodes:
        sorted_funcs = sorted(call_graph.items(), key=lambda x: len(x[1]), reverse=True)
        selected_nodes = [caller for caller, _ in sorted_funcs[:max_nodes]]

    rendered_nodes = set()

    for caller in selected_nodes:
        callees = call_graph.get(caller, [])
        caller_id = sanitize_id(caller)

        if caller in entry_points:
            lines.append(f"    {caller_id}[{caller}]")
        else:
            lines.append(f"    {caller_id}(({caller}))")
        rendered_nodes.add(caller)

        for callee in callees[:5]:
            callee_id = sanitize_id(callee)
            if callee not in rendered_nodes and callee not in call_graph:
                lines.append(f"    {callee_id}[{callee}]")
                rendered_nodes.add(callee)
            lines.append(f"    {caller_id} --> {callee_id}")

    lines.append("    end")

    return "\n".join(lines)
