from typing import Any, Callable


GetNodeName = Callable[[Any, str], str | None]
ExtractParams = Callable[[Any, str, str], list[str]]
ExtractCalls = Callable[[Any, str], list[str]]
ExtractDocstring = Callable[[Any, str], str | None]
ExtractDecorators = Callable[[Any, str], list[str]]
ExtractReturnType = Callable[[Any, str], str | None]
ExtractModifiers = Callable[[Any, str], list[str]]


def extract_generic(
    source: str,
    node: Any,
    symbols: list[dict[str, Any]],
    current_class: str | None,
    func_types: str | tuple[str, ...] | list[str] | set[str],
    class_types: str | tuple[str, ...] | list[str] | set[str],
    extra_types: tuple[str, ...],
    get_node_name: GetNodeName,
    extract_params: ExtractParams,
    extract_calls: ExtractCalls,
    extract_docstring: ExtractDocstring,
    extract_decorators: ExtractDecorators,
    extract_return_type: ExtractReturnType,
    extract_modifiers: ExtractModifiers,
) -> None:
    node_type = node.type

    func_type_set = {func_types} if isinstance(func_types, str) else set(func_types)
    class_type_set = {class_types} if isinstance(class_types, str) else set(class_types)

    if node_type in func_type_set:
        name = get_node_name(node, source)
        if name:
            params = extract_params(node, source, node_type)
            calls = extract_calls(node, source)
            doc = extract_docstring(node, source)
            decorators = extract_decorators(node, source)
            return_type = extract_return_type(node, source)
            modifiers = extract_modifiers(node, source)

            sym_type = "function"
            if current_class:
                sym_type = "method"

            sym = {
                "name": name,
                "type": sym_type,
                "line": node.start_point.row + 1,
                "params": params,
                "calls": calls,
                "class": current_class,
                "parent": current_class,
            }
            if doc:
                sym["doc"] = doc
            if decorators:
                sym["decorators"] = decorators
            if return_type:
                sym["return_type"] = return_type
            if modifiers:
                sym["modifiers"] = modifiers
            symbols.append(sym)

    elif node_type in class_type_set:
        name = get_node_name(node, source)
        if name:
            methods = []
            class_calls = []
            doc = extract_docstring(node, source)
            decorators = extract_decorators(node, source)
            modifiers = extract_modifiers(node, source)

            for child in node.children:
                if child.type in func_type_set or (extra_types and child.type in extra_types):
                    method_name = get_node_name(child, source)
                    if method_name:
                        params = extract_params(child, source, child.type)
                        method_calls = extract_calls(child, source)
                        method_doc = extract_docstring(child, source)
                        method_decorators = extract_decorators(child, source)
                        method_return_type = extract_return_type(child, source)
                        method_modifiers = extract_modifiers(child, source)
                        method = {
                            "name": method_name,
                            "type": "method",
                            "line": child.start_point.row + 1,
                            "params": params,
                            "calls": method_calls,
                            "class": name,
                            "parent": name,
                        }
                        if method_doc:
                            method["doc"] = method_doc
                        if method_decorators:
                            method["decorators"] = method_decorators
                        if method_return_type:
                            method["return_type"] = method_return_type
                        if method_modifiers:
                            method["modifiers"] = method_modifiers
                        methods.append(method)
                        class_calls.extend(method_calls)

            sym = {
                "name": name,
                "type": "class",
                "line": node.start_point.row + 1,
                "methods": methods,
                "calls": list(set(class_calls)),
            }
            if doc:
                sym["doc"] = doc
            if decorators:
                sym["decorators"] = decorators
            if modifiers:
                sym["modifiers"] = modifiers
            symbols.append(sym)

            current_class = name

    for child in node.children:
        extract_generic(
            source,
            child,
            symbols,
            current_class,
            func_types,
            class_types,
            extra_types,
            get_node_name,
            extract_params,
            extract_calls,
            extract_docstring,
            extract_decorators,
            extract_return_type,
            extract_modifiers,
        )
