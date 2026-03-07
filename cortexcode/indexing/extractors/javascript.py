from typing import Any, Callable


GetNodeName = Callable[[Any, str], str | None]
ExtractParams = Callable[[Any, str, str], list[str]]
ExtractCalls = Callable[[Any, str], list[str]]
ExtractReturnType = Callable[[Any, str], str | None]
ExtractJSDoc = Callable[[Any, str], str | None]
DetectFramework = Callable[[str, Any, str], str | None]
DetectClassFramework = Callable[[str, Any, str], str | None]


def extract_js_ts_generic(
    source: str,
    node: Any,
    symbols: list[dict[str, Any]],
    current_class: str | None,
    is_ts: bool,
    get_node_name: GetNodeName,
    extract_params: ExtractParams,
    extract_calls: ExtractCalls,
    extract_return_type: ExtractReturnType,
    extract_jsdoc: ExtractJSDoc,
    detect_framework: DetectFramework,
    detect_class_framework: DetectClassFramework,
) -> None:
    node_type = node.type

    if node_type == "function_declaration":
        name = get_node_name(node, source)
        if name:
            params = extract_params(node, source, node_type)
            calls = extract_calls(node, source)
            doc = extract_jsdoc(node, source)

            sym_type = "method" if current_class else "function"
            framework = detect_framework(name, node, source)

            sym = {
                "name": name,
                "type": sym_type,
                "line": node.start_point.row + 1,
                "params": params,
                "calls": calls,
                "class": current_class,
                "framework": framework,
            }
            if doc:
                sym["doc"] = doc
            symbols.append(sym)

    elif node_type in ("lexical_declaration", "variable_declaration"):
        for child in node.children:
            if child.type == "variable_declarator":
                name_node = child.child_by_field_name("name")
                value_node = child.child_by_field_name("value")

                if name_node and value_node:
                    name = name_node.text.decode("utf-8")

                    if value_node.type in ("arrow_function", "function_expression", "function"):
                        params = extract_params(value_node, source, value_node.type)
                        calls = extract_calls(value_node, source)
                        return_type = extract_return_type(value_node, source) if is_ts else None
                        doc = extract_jsdoc(node, source)

                        sym_type = "method" if current_class else "function"
                        framework = detect_framework(name, value_node, source)

                        sym = {
                            "name": name,
                            "type": sym_type,
                            "line": node.start_point.row + 1,
                            "params": params,
                            "calls": calls,
                            "class": current_class,
                            "framework": framework,
                        }
                        if return_type:
                            sym["return_type"] = return_type
                        if doc:
                            sym["doc"] = doc
                        symbols.append(sym)

                    elif value_node.type == "call_expression":
                        pass

    elif node_type in ("export_statement", "export_default_declaration"):
        for child in node.children:
            extract_js_ts_generic(
                source,
                child,
                symbols,
                current_class,
                is_ts,
                get_node_name,
                extract_params,
                extract_calls,
                extract_return_type,
                extract_jsdoc,
                detect_framework,
                detect_class_framework,
            )
        return

    elif node_type in ("class_declaration", "class_expression"):
        name = get_node_name(node, source)
        if name:
            methods = []
            class_calls = []

            for child in node.children:
                if child.type == "class_body":
                    for member in child.children:
                        if member.type in ("method_definition", "public_field_definition", "field_definition"):
                            method_name = get_node_name(member, source)
                            if method_name:
                                params = extract_params(member, source, member.type)
                                method_calls = extract_calls(member, source)
                                methods.append({
                                    "name": method_name,
                                    "type": "method",
                                    "line": member.start_point.row + 1,
                                    "params": params,
                                    "calls": method_calls,
                                })
                                class_calls.extend(method_calls)

            framework = detect_class_framework(name, node, source)

            symbols.append({
                "name": name,
                "type": "class",
                "line": node.start_point.row + 1,
                "methods": methods,
                "calls": list(set(class_calls)),
                "framework": framework,
            })

            current_class = name

    elif is_ts and node_type == "interface_declaration":
        name = get_node_name(node, source)
        if name:
            members = []
            for child in node.children:
                if child.type == "object_type" or child.type == "interface_body":
                    for member in child.children:
                        prop_name = get_node_name(member, source)
                        if prop_name:
                            members.append(prop_name)
            symbols.append({
                "name": name,
                "type": "interface",
                "line": node.start_point.row + 1,
                "members": members if members else None,
                "framework": "typescript",
            })

    elif is_ts and node_type == "type_alias_declaration":
        name = get_node_name(node, source)
        if name:
            symbols.append({
                "name": name,
                "type": "type",
                "line": node.start_point.row + 1,
                "framework": "typescript",
            })

    elif is_ts and node_type == "enum_declaration":
        name = get_node_name(node, source)
        if name:
            symbols.append({
                "name": name,
                "type": "enum",
                "line": node.start_point.row + 1,
                "framework": "typescript",
            })

    for child in node.children:
        extract_js_ts_generic(
            source,
            child,
            symbols,
            current_class,
            is_ts,
            get_node_name,
            extract_params,
            extract_calls,
            extract_return_type,
            extract_jsdoc,
            detect_framework,
            detect_class_framework,
        )
