from typing import Any, Callable


GetNodeName = Callable[[Any, str], str | None]
ExtractParams = Callable[[Any, str, str], list[str]]
ExtractCalls = Callable[[Any, str], list[str]]
DetectSwiftFramework = Callable[[str, Any, str], str | None]


def extract_swift_recursive(
    source: str,
    node: Any,
    symbols: list[dict[str, Any]],
    current_class: str | None,
    get_node_name: GetNodeName,
    extract_params: ExtractParams,
    extract_calls: ExtractCalls,
    detect_swift_framework: DetectSwiftFramework,
) -> None:
    node_type = node.type

    if node_type == "function_declaration":
        name = get_node_name(node, source)
        if name:
            params = extract_params(node, source, node_type)
            calls = extract_calls(node, source)
            framework = detect_swift_framework(name, node, source)
            sym_type = "method" if current_class else "function"
            symbols.append({
                "name": name,
                "type": sym_type,
                "line": node.start_point.row + 1,
                "params": params,
                "calls": calls,
                "class": current_class,
                "framework": framework,
            })

    elif node_type == "class_declaration":
        name = get_node_name(node, source)
        if name:
            methods = []
            class_calls = []
            for child in node.children:
                if child.type == "class_body":
                    for member in child.children:
                        if member.type == "function_declaration":
                            method_name = get_node_name(member, source)
                            if method_name:
                                method_params = extract_params(member, source, member.type)
                                method_calls = extract_calls(member, source)
                                methods.append({
                                    "name": method_name,
                                    "type": "method",
                                    "line": member.start_point.row + 1,
                                    "params": method_params,
                                    "calls": method_calls,
                                })
                                class_calls.extend(method_calls)

            framework = detect_swift_framework(name, node, source)
            symbols.append({
                "name": name,
                "type": "class",
                "line": node.start_point.row + 1,
                "methods": methods,
                "calls": list(set(class_calls)),
                "framework": framework,
            })
            current_class = name

    elif node_type == "protocol_declaration":
        name = get_node_name(node, source)
        if name:
            symbols.append({
                "name": name,
                "type": "interface",
                "line": node.start_point.row + 1,
                "framework": "swift",
            })

    elif node_type == "struct_declaration":
        name = get_node_name(node, source)
        if name:
            framework = detect_swift_framework(name, node, source)
            symbols.append({
                "name": name,
                "type": "class",
                "line": node.start_point.row + 1,
                "framework": framework,
            })

    elif node_type == "enum_declaration":
        name = get_node_name(node, source)
        if name:
            symbols.append({
                "name": name,
                "type": "enum",
                "line": node.start_point.row + 1,
            })

    for child in node.children:
        extract_swift_recursive(
            source,
            child,
            symbols,
            current_class,
            get_node_name,
            extract_params,
            extract_calls,
            detect_swift_framework,
        )
