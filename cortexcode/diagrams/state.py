from typing import Any


def generate_state_diagram(index_data: dict[str, Any]) -> str:
    files = index_data.get("files", {})

    lines = ["stateDiagram-v2"]
    lines.append("    [*] --> Initial")

    state_funcs = []
    for path, data in files.items():
        symbols = data.get("symbols", []) if isinstance(data, dict) else data
        for sym in symbols:
            name = sym.get("name", "").lower()
            if any(kw in name for kw in ["init", "start", "create", "handle", "process"]):
                state_funcs.append(sym.get("name"))

    for func in state_funcs[:10]:
        lines.append(f"    Initial --> {func}")
        lines.append(f"    {func} --> [*]")

    return "\n".join(lines)
