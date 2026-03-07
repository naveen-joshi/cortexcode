from typing import Any, Callable


GetNodeName = Callable[[Any, str], str | None]
ExtractParams = Callable[[Any, str, str], list[str]]
ExtractCalls = Callable[[Any, str], list[str]]
DetectJavaFramework = Callable[[str, Any, str], str | None]


def extract_java_with_framework(
    source: str,
    node: Any,
    symbols: list[dict[str, Any]],
    current_class: str | None,
    get_node_name: GetNodeName,
    extract_params: ExtractParams,
    extract_calls: ExtractCalls,
    detect_java_framework: DetectJavaFramework,
) -> None:
    node_type = node.type

    if node_type == "method_declaration":
        name = get_node_name(node, source)
        if name:
            params = extract_params(node, source, node_type)
            calls = extract_calls(node, source)

            symbols.append({
                "name": name,
                "type": "method",
                "line": node.start_point.row + 1,
                "params": params,
                "calls": calls,
                "class": current_class,
            })

    elif node_type == "class_declaration":
        name = get_node_name(node, source)
        if name:
            methods = []
            class_calls = []

            for child in node.children:
                if child.type == "method_declaration":
                    method_name = get_node_name(child, source)
                    if method_name:
                        params = extract_params(child, source, child.type)
                        method_calls = extract_calls(child, source)
                        methods.append({
                            "name": method_name,
                            "type": "method",
                            "line": child.start_point.row + 1,
                            "params": params,
                            "calls": method_calls,
                        })
                        class_calls.extend(method_calls)

            framework = detect_java_framework(name, node, source)

            symbols.append({
                "name": name,
                "type": "class",
                "line": node.start_point.row + 1,
                "methods": methods,
                "calls": list(set(class_calls)),
                "framework": framework,
            })

            current_class = name

    elif node_type == "interface_declaration":
        name = get_node_name(node, source)
        if name:
            symbols.append({
                "name": name,
                "type": "interface",
                "line": node.start_point.row + 1,
                "framework": detect_java_framework(name, node, source),
            })

    for child in node.children:
        extract_java_with_framework(
            source,
            child,
            symbols,
            current_class,
            get_node_name,
            extract_params,
            extract_calls,
            detect_java_framework,
        )
