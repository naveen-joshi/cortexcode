from pathlib import Path
from typing import Any


def generate_flow_docs(index: dict[str, Any], output_path: Path) -> None:
    call_graph = index.get("call_graph", {})

    callers = {}
    for caller, callees in call_graph.items():
        for callee in callees:
            if callee not in callers:
                callers[callee] = []
            callers[callee].append(caller)

    lines = [
        "# Call Flows",
        "",
        "## Call Graph",
        "",
    ]

    top_level = set(call_graph.keys()) - set(callers.keys())
    if top_level:
        lines.append("### Entry Points (top-level functions)")
        lines.append("")
        for symbol in sorted(top_level)[:10]:
            calls = call_graph.get(symbol, [])
            lines.append(f"- `{symbol}` → {', '.join(calls[:5]) if calls else 'no calls'}")
        lines.append("")

    lines.append("### Most Called Functions")
    lines.append("")
    sorted_by_callers = sorted(callers.items(), key=lambda x: len(x[1]), reverse=True)
    for symbol, symbol_callers in sorted_by_callers[:10]:
        lines.append(f"- `{symbol}` called by {len(symbol_callers)} functions")
    lines.append("")

    lines.append("## Full Call Graph")
    lines.append("")

    for symbol, calls in sorted(call_graph.items()):
        if calls:
            lines.append(f"### {symbol}")
            lines.append("")
            symbol_callers = callers.get(symbol, [])
            if symbol_callers:
                lines.append(f"**Called by:** {', '.join(symbol_callers[:5])}")
                lines.append("")
            lines.append("**Calls:**")
            for call in calls:
                lines.append(f"  → `{call}`")
            lines.append("")

    if not any(call_graph.values()):
        lines.append("*No call relationships found.*")

    output_path.write_text("\n".join(lines), encoding="utf-8")
