def format_context_for_ai(result: dict) -> str:
    """Format context as a text block suitable for pasting into AI chat."""
    lines = ["## Relevant Code Context\n"]

    for sym in result.get("symbols", []):
        lines.append(f"### {sym['name']} ({sym.get('type', 'unknown')})")
        lines.append(f"**File:** `{sym.get('file', 'unknown')}:{sym.get('line', '?')}`")

        if sym.get("params"):
            lines.append(f"**Params:** {', '.join(sym['params'])}")

        if sym.get("calls"):
            lines.append(f"**Calls:** {', '.join(sym['calls'])}")

        lines.append("")

    return "\n".join(lines)
