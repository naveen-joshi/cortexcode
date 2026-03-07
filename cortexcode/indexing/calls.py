from typing import Any


def find_calls_recursive(node: Any, calls: list[str]) -> None:
    if node.type in ("call", "call_expression"):
        func = node.child_by_field_name("function") or (node.children[0] if node.children else None)
        if func:
            if func.type == "identifier":
                calls.append(func.text.decode("utf-8"))
            elif func.type in ("member_expression", "attribute"):
                prop = func.child_by_field_name("property") or func.child_by_field_name("attribute")
                if prop:
                    calls.append(prop.text.decode("utf-8"))
                else:
                    for child in reversed(func.children):
                        if child.type in ("identifier", "property_identifier"):
                            calls.append(child.text.decode("utf-8"))
                            break
            elif func.type == "attribute_expression":
                attr = func.child_by_field_name("attribute")
                if attr:
                    calls.append(attr.text.decode("utf-8"))

    for child in node.children:
        find_calls_recursive(child, calls)
