from pathlib import Path
from typing import Any


def generate_structure_docs(index: dict[str, Any], output_path: Path) -> None:
    files = index.get("files", {})

    lines = [
        "# Project Structure",
        "",
        "```",
    ]

    for rel_path in sorted(files.keys()):
        lines.append(rel_path)

    lines.append("```")

    output_path.write_text("\n".join(lines), encoding="utf-8")
