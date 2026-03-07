import re
from typing import Any, Callable


GetNodeName = Callable[[Any, str], str | None]


def extract_imports(source: str, node: Any, ext: str) -> list[dict[str, Any]]:
    imports: list[dict[str, Any]] = []

    if ext in (".js", ".jsx", ".ts", ".tsx"):
        find_js_imports(node, imports)
    elif ext == ".py":
        return extract_python_imports_from_source(source)

    return imports


def extract_python_imports_from_source(source: str) -> list[dict[str, Any]]:
    imports: list[dict[str, Any]] = []

    for raw_line in source.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        from_match = re.match(r"from\s+([\.\w]+)\s+import\s+(.+)", line)
        if from_match:
            module_name = from_match.group(1).strip()
            imported_clause = from_match.group(2).strip().strip("()")
            imported = []
            for chunk in imported_clause.split(","):
                cleaned = chunk.strip()
                if not cleaned:
                    continue
                if cleaned == "*":
                    imported.append("*")
                    continue
                imported.append(cleaned.split(" as ", 1)[0].strip())
            imports.append({
                "module": module_name,
                "imported": imported,
            })
            continue

        import_match = re.match(r"import\s+(.+)", line)
        if import_match:
            for chunk in import_match.group(1).split(","):
                cleaned = chunk.strip()
                if not cleaned:
                    continue
                module_name = cleaned.split(" as ", 1)[0].strip()
                imports.append({
                    "module": module_name,
                    "imported": [module_name.split(".")[-1]],
                })

    return imports


def find_js_imports(node: Any, imports: list[dict[str, Any]]) -> None:
    if node.type == "import_statement":
        module_name = None
        imported = []

        for child in node.children:
            if child.type == "string":
                module_name = child.text.decode("utf-8").strip('"\'')
            elif child.type == "import_clause":
                for clause_child in child.children:
                    if clause_child.type == "identifier":
                        imported.append(clause_child.text.decode("utf-8"))
                    elif clause_child.type == "named_imports":
                        for import_child in clause_child.children:
                            if import_child.type == "import_specifier":
                                name = import_child.child_by_field_name("name")
                                if name:
                                    imported.append(name.text.decode("utf-8"))

        if module_name:
            imports.append({
                "module": module_name,
                "imported": imported,
                "default": imported[0] if imported else None,
            })

    for child in node.children:
        find_js_imports(child, imports)


def find_python_imports(node: Any, imports: list[dict[str, Any]]) -> None:
    if node.type in ("import_statement", "import_from_statement"):
        module_name = None
        imported = []

        for child in node.children:
            if child.type == "dotted_name":
                module_name = child.text.decode("utf-8")
            elif child.type == "aliased_import":
                for alias_child in child.children:
                    if alias_child.type == "identifier":
                        imported.append(alias_child.text.decode("utf-8"))
            elif child.type == "wildcard_import":
                imported.append("*")
            elif child.type == "dotted_name" and node.type == "import_from_statement":
                for dotted_child in child.children:
                    if dotted_child.type == "identifier":
                        imported.append(dotted_child.text.decode("utf-8"))

        if module_name:
            imports.append({
                "module": module_name,
                "imported": imported,
            })

    for child in node.children:
        find_python_imports(child, imports)


def extract_exports(source: str, node: Any, ext: str, get_node_name: GetNodeName) -> list[dict[str, Any]]:
    exports: list[dict[str, Any]] = []

    if ext in (".js", ".jsx", ".ts", ".tsx"):
        find_js_exports(node, exports, get_node_name)
    elif ext == ".py":
        find_python_exports(node, exports)

    return exports


def find_js_exports(node: Any, exports: list[dict[str, Any]], get_node_name: GetNodeName) -> None:
    if node.type == "export_statement":
        for child in node.children:
            if child.type == "named_export":
                for export_child in child.children:
                    if export_child.type == "export_clause":
                        for export_clause_child in export_child.children:
                            if export_clause_child.type == "export_specifier":
                                name = export_clause_child.child_by_field_name("name")
                                if name:
                                    exports.append({"name": name.text.decode("utf-8"), "type": "named"})
            elif child.type == "variable_declaration":
                for declaration_child in child.children:
                    if declaration_child.type == "variable_declarator":
                        name_node = declaration_child.child_by_field_name("name")
                        if name_node:
                            exports.append({"name": name_node.text.decode("utf-8"), "type": "variable"})
            elif child.type == "class_declaration":
                name_node = get_node_name(child, "")
                if name_node:
                    exports.append({"name": name_node, "type": "class"})
            elif child.type == "function_declaration":
                name_node = get_node_name(child, "")
                if name_node:
                    exports.append({"name": name_node, "type": "function"})

    for child in node.children:
        find_js_exports(child, exports, get_node_name)


def find_python_exports(node: Any, exports: list[dict[str, Any]]) -> None:
    if node.type == "assignment_statement":
        for child in node.children:
            if child.type == "attribute" and child.text.decode("utf-8") == "__all__":
                for export_child in child.children:
                    if export_child.type == "list":
                        for list_child in export_child.children:
                            if list_child.type == "string":
                                exports.append({"name": list_child.text.decode("utf-8").strip('"\''), "type": "explicit"})

    for child in node.children:
        find_python_exports(child, exports)
