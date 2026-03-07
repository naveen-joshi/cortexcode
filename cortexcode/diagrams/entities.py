from typing import Any


def generate_entity_diagram(index_data: dict[str, Any]) -> str:
    files = index_data.get("files", {})
    project_profile = index_data.get("project_profile", {})

    lines = ["erDiagram"]
    lines.append("    %% Database Entity Relationship Diagram")

    profile_entities = project_profile.get("entity_samples", [])
    if profile_entities:
        entity_names = []
        for entity in profile_entities:
            entity_name = str(entity.get("name", "unknown"))
            lines.append(f"    {entity_name} {{")
            fields = entity.get("fields", []) if isinstance(entity.get("fields"), list) else []
            for field in fields[:8]:
                lines.append(f"        string {field}")
            lines.append("    }")
            entity_names.append(entity_name)

        if len(entity_names) <= 1:
            return "\n".join(lines)

        for left_name, right_name in zip(entity_names, entity_names[1:]):
            lines.append(f"    {left_name} ||--o{{ {right_name} : relates_to")
        return "\n".join(lines)

    entities = []

    for path, data in files.items():
        symbols = data.get("symbols", []) if isinstance(data, dict) else data

        for sym in symbols:
            sym_type = sym.get("type", "")
            name = sym.get("name", "")

            is_entity = False
            if any(kw in name.lower() for kw in ["model", "entity", "schema", "table"]):
                is_entity = True
            if "decorators" in sym and any("table" in str(d).lower() or "model" in str(d).lower() for d in sym.get("decorators", [])):
                is_entity = True

            if is_entity or sym_type == "class":
                lines.append(f"    {name} {{")

                methods = [
                    s for s in symbols
                    if s.get("type") == "method" and (s.get("parent") == name or s.get("class") == name)
                ]
                for m in methods[:5]:
                    ret = m.get("return_type", "string")
                    lines.append(f"        {ret} {m.get('name')}")

                lines.append("    }")
                entities.append(name)

    for path, data in files.items():
        symbols = data.get("symbols", []) if isinstance(data, dict) else data

        for sym in symbols:
            if sym.get("type") == "class" and sym.get("name") in entities:
                class_name = sym.get("name")
                methods = [
                    s.get("name", "")
                    for s in symbols
                    if s.get("type") == "method" and (s.get("parent") == class_name or s.get("class") == class_name)
                ]

                for m in methods:
                    for other_entity in entities:
                        if other_entity != class_name and other_entity.lower() in m.lower():
                            if "many" in m.lower() or "list" in m.lower() or "[]" in m:
                                lines.append(f"    {class_name} ||--o{{ {other_entity} : has")
                            else:
                                lines.append(f"    {class_name} ||--|| {other_entity} : has")

    if not entities:
        lines.append("    %% No entities detected")
        lines.append("    %% Add classes with 'Model', 'Entity', or 'Schema' in name")

    return "\n".join(lines)
