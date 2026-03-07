from typing import Any

from cortexcode.diagrams.utils import sanitize_id


def generate_sequence_diagram(index_data: dict[str, Any], entry_point: str = "main") -> str:
    call_graph = index_data.get("call_graph", {})
    project_profile = index_data.get("project_profile", {})

    suggested_entry_points = [
        item.get("name") for item in project_profile.get("entry_points", []) if item.get("name") in call_graph
    ]
    if entry_point not in call_graph:
        entry_point = suggested_entry_points[0] if suggested_entry_points else list(call_graph.keys())[0] if call_graph else "start"

    lines = ["sequenceDiagram"]
    lines.append(f"    participant Main as {entry_point}")

    visited = {entry_point}
    queue = list(call_graph.get(entry_point, []))[:10]

    participant_count = 1
    participants = {entry_point: "Main"}

    while queue and participant_count < 15:
        callee = queue.pop(0)
        if callee in visited:
            continue

        participant_count += 1
        participant_id = f"Participant{participant_count}"
        participants[callee] = participant_id
        lines.append(f"    participant {participant_id} as {callee[:30]}")
        visited.add(callee)

        for next_callee in call_graph.get(callee, [])[:3]:
            if next_callee not in visited:
                queue.append(next_callee)

    for caller, callees in call_graph.items():
        caller_id = participants.get(caller, sanitize_id(caller))
        for callee in callees[:3]:
            callee_id = participants.get(callee, sanitize_id(callee))
            lines.append(f"    {caller_id}->>+{callee_id}: call")
            lines.append(f"    {callee_id}-->>-{caller_id}: return")

    return "\n".join(lines)
