from typing import Any


def get_node_name(node: Any) -> str | None:
    for child in node.children:
        if child.type == "identifier":
            return child.text.decode("utf-8")
    return None
