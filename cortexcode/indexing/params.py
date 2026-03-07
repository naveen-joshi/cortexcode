from typing import Any


def extract_params(func_node: Any) -> list[str]:
    params = []

    for child in func_node.children:
        if child.type == "parameters":
            for param in child.children:
                if param.type == "identifier":
                    params.append(param.text.decode("utf-8"))
                elif param.type in (
                    "optional_parameter",
                    "rest_parameter",
                    "spread_element",
                    "typed_parameter",
                    "default_parameter",
                    "keyword_argument",
                    "parameter",
                    "receiver",
                ):
                    for param_child in param.children:
                        if param_child.type == "identifier":
                            params.append(param_child.text.decode("utf-8"))
                            break

    return params
