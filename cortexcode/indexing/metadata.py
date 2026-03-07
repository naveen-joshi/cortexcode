from typing import Any


def extract_docstring(node: Any) -> str | None:
    for child in node.children:
        if child.type == "block":
            for block_child in child.children:
                if block_child.type == "expression_statement":
                    for expr_child in block_child.children:
                        if expr_child.type == "string":
                            doc = expr_child.text.decode("utf-8", errors="ignore")
                            doc = doc.strip('"').strip("'").strip()
                            if doc:
                                return doc[:200] + "..." if len(doc) > 200 else doc
                    break
            break
    return None


def extract_decorators(node: Any) -> list[str]:
    decorators = []
    for child in node.children:
        if child.type == "decorator":
            decorator_text = child.text.decode("utf-8", errors="ignore").strip()
            if decorator_text and not decorator_text.startswith("@"):
                decorator_text = "@" + decorator_text
            if decorator_text:
                decorators.append(decorator_text)
    return decorators


def extract_return_type(node: Any) -> str | None:
    type_annotation = node.child_by_field_name("return_type")
    if type_annotation:
        return type_annotation.text.decode("utf-8", errors="ignore").lstrip(": ").strip()

    params_node = node.child_by_field_name("parameters")
    params_end = params_node.end_byte if params_node else -1
    for child in node.children:
        if child.start_byte <= params_end:
            continue
        if child.type in ("type", "annotation"):
            return child.text.decode("utf-8", errors="ignore").lstrip(": ").strip()
    return None


def extract_modifiers(node: Any) -> list[str]:
    modifiers = []
    for child in node.children:
        if child.type in ("async", "static", "public", "private", "protected", "abstract", "override"):
            modifiers.append(child.text.decode("utf-8", errors="ignore"))
    return modifiers


def extract_jsdoc(node: Any, source: str) -> str | None:
    start_line = node.start_point.row
    source_lines = source.split("\n")

    doc_lines = []
    in_jsdoc = False
    for i in range(start_line - 1, max(start_line - 15, -1), -1):
        if i < 0 or i >= len(source_lines):
            break
        line = source_lines[i].strip()

        if line.endswith("*/"):
            in_jsdoc = True
            line = line[:-2].strip()
            if line:
                doc_lines.insert(0, line.lstrip("* "))
        elif in_jsdoc:
            if line.startswith("/**"):
                line = line[3:].strip()
                if line:
                    doc_lines.insert(0, line.lstrip("* "))
                break
            elif line.startswith("/*"):
                line = line[2:].strip()
                if line:
                    doc_lines.insert(0, line.lstrip("* "))
                break
            elif line.startswith("*"):
                line = line[1:].strip()
                if line and not line.startswith("@"):
                    doc_lines.insert(0, line)
            else:
                break
        elif line.startswith("//"):
            doc_lines.insert(0, line[2:].strip())
        elif line == "":
            if doc_lines:
                break
            continue
        else:
            break

    if doc_lines:
        doc = " ".join(doc_lines).strip()
        return doc[:200] + "..." if len(doc) > 200 else doc
    return None
