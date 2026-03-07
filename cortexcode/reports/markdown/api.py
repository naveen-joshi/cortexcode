from pathlib import Path
from typing import Any


def generate_api_docs(index: dict[str, Any], output_path: Path) -> None:
    files = index.get("files", {})

    lines = [
        "# API Documentation",
        "",
    ]

    for rel_path, file_data in sorted(files.items()):
        symbols = file_data.get("symbols", []) if isinstance(file_data, dict) else file_data
        if not symbols:
            continue

        lines.append(f"## {rel_path}")
        lines.append("")

        for sym in symbols:
            name = sym.get("name", "unknown")
            sym_type = sym.get("type", "function")
            params = sym.get("params", [])
            doc = sym.get("doc", "")
            decorators = sym.get("decorators", [])
            return_type = sym.get("return_type")
            modifiers = sym.get("modifiers", [])

            params_str = ", ".join(params) if params else ""

            if sym_type == "class":
                lines.append(f"### class `{name}`")
            else:
                prefix = f"{' '.join(modifiers)} " if modifiers else ""
                ret_str = f" -> {return_type}" if return_type else ""
                lines.append(f"### `{prefix}{name}({params_str}){ret_str}`")

            lines.append("")

            if decorators:
                for dec in decorators:
                    lines.append(f"**{dec}**")
                lines.append("")

            if doc:
                lines.append(f"> {doc}")
                lines.append("")

            if sym.get("methods"):
                lines.append("**Methods:**")
                for method in sym.get("methods", []):
                    method_params = ", ".join(method.get("params", []))
                    m_ret = f" -> {method.get('return_type', '')}" if method.get("return_type") else ""
                    lines.append(f"- `{method.get('name', '')}({method_params}){m_ret}`")
                lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
