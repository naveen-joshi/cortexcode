from typing import Any

from cortexcode.diagrams.utils import STYLE_CLASS, STYLE_FUNCTION, STYLE_INTERFACE


def generate_class_diagram(index_data: dict[str, Any]) -> str:
    files = index_data.get("files", {})
    imports = index_data.get("imports", {})

    lines = ["classDiagram"]
    lines.append("    %% Class Diagram")
    lines.append(STYLE_CLASS)
    lines.append(STYLE_FUNCTION)
    lines.append(STYLE_INTERFACE)

    classes = []
    relationships = []

    for path, data in files.items():
        symbols = data.get("symbols", []) if isinstance(data, dict) else data

        for sym in symbols:
            if sym.get("type") == "class":
                class_name = sym.get("name", "Unknown")
                lines.append(f"    class {class_name} {{")

                methods = [
                    s for s in symbols
                    if s.get("type") == "method" and (s.get("parent") == class_name or s.get("class") == class_name)
                ]
                for m in methods[:10]:
                    ret = m.get("return_type", "")
                    params = ", ".join(m.get("params", [])[:3])
                    modifiers = m.get("modifiers", [])
                    vis = "+"
                    if "private" in modifiers:
                        vis = "-"
                    elif "protected" in modifiers:
                        vis = "#"
                    lines.append(f"        {vis}{m.get('name')}({params}) {ret}")

                decorators = sym.get("decorators", [])
                if decorators:
                    lines.append(f"        <<decorator>> {', '.join(decorators)}")

                lines.append("    }")
                classes.append(class_name)

    for path, data in files.items():
        symbols = data.get("symbols", []) if isinstance(data, dict) else data
        for sym in symbols:
            if sym.get("type") == "class":
                class_name = sym.get("name", "Unknown")
                for other_path, other_data in files.items():
                    other_symbols = other_data.get("symbols", []) if isinstance(other_data, dict) else other_data
                    for other_sym in other_symbols:
                        if other_sym.get("type") == "class" and other_sym.get("name") != class_name:
                            if class_name in str(other_sym.get("doc", "")):
                                relationships.append(f"    {class_name} <|-- {other_sym.get('name')}")

    lines.extend(relationships[:10])

    return "\n".join(lines)
