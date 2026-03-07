from typing import Any


def generate_file_tree_diagram(index_data: dict[str, Any], max_depth: int = 3) -> str:
    files = index_data.get("files", {})

    lines = ["graph TD"]
    lines.append("    %% File Tree Structure")

    tree: dict[str, Any] = {}
    for path in sorted(files.keys())[:50]:
        parts = path.split("/")
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]

    def render_tree(node: dict[str, Any], prefix: str = "", depth: int = 0) -> list[str]:
        result = []
        items = sorted(node.items())
        for i, (name, children) in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            result.append(f"    {prefix}{connector}{name}")
            if children and depth < max_depth:
                new_prefix = prefix + ("    " if is_last else "│   ")
                result.extend(render_tree(children, new_prefix, depth + 1))
        return result

    lines.extend(render_tree(tree))

    return "\n".join(lines)
