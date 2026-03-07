from typing import Any, Callable


GetNodeName = Callable[[Any, str], str | None]


def extract_entities(source: str, node: Any, ext: str, get_node_name: GetNodeName) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []

    if ext in (".js", ".jsx", ".ts", ".tsx"):
        find_js_entities(node, entities, source, get_node_name)
    elif ext == ".py":
        find_python_entities(node, entities, source, get_node_name)

    return entities


def find_js_entities(node: Any, entities: list[dict[str, Any]], source: str, get_node_name: GetNodeName) -> None:
    source_bytes = node.text if hasattr(node, "text") else b""
    source_str = source_bytes.decode("utf-8", errors="ignore")

    if node.type == "class_declaration":
        name = get_node_name(node, source_str)
        if name:
            entity_type = "unknown"
            if "@Entity" in source_str:
                entity_type = "typeorm"
            elif "sequelize" in source_str.lower() or "Model" in name:
                entity_type = "sequelize"
            elif "prisma" in source_str.lower() or "@Model" in source_str:
                entity_type = "prisma"

            fields = []
            for child in node.children:
                if child.type == "class_body":
                    for cb in child.children:
                        if cb.type == "field_definition":
                            field_name = get_node_name(cb, source_str)
                            if field_name:
                                fields.append(field_name)

            entities.append({
                "name": name,
                "type": entity_type,
                "fields": fields,
            })

    for child in node.children:
        find_js_entities(child, entities, source_str, get_node_name)


def find_python_entities(node: Any, entities: list[dict[str, Any]], source: str, get_node_name: GetNodeName) -> None:
    source_bytes = node.text if hasattr(node, "text") else b""
    source_str = source_bytes.decode("utf-8", errors="ignore")

    if node.type == "class_definition":
        name = get_node_name(node, source_str)
        if name:
            entity_type = "unknown"
            if "SQLModel" in source_str or "Base" in source_str:
                entity_type = "sqlmodel"
            elif "Flask" in source_str or "SQLAlchemy" in source_str:
                entity_type = "sqlalchemy"
            elif "Django" in source_str:
                entity_type = "django"
            elif "Pydantic" in source_str:
                entity_type = "pydantic"

            fields = []
            for child in node.children:
                if child.type == "block":
                    for bc in child.children:
                        if bc.type == "expression_statement":
                            for bcc in bc.children:
                                if bcc.type == "assignment":
                                    for bcca in bcc.children:
                                        if bcca.type == "identifier":
                                            fields.append(bcca.text.decode("utf-8"))

            entities.append({
                "name": name,
                "type": entity_type,
                "fields": fields,
            })

    for child in node.children:
        find_python_entities(child, entities, source_str, get_node_name)
