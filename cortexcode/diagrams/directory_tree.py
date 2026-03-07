from collections import defaultdict
from pathlib import Path
from typing import Any


def generate_directory_tree(index_data: dict[str, Any]) -> str:
    files = index_data.get("files", {})

    dirs: dict[str, list[str]] = defaultdict(list)
    for path in files.keys():
        parts = path.split("/")
        if len(parts) > 1:
            dirs[parts[0]].append(path)
        else:
            dirs["."].append(path)

    lines = ["mindmap"]
    lines.append("    root((Project))")

    for dir_name, dir_files in sorted(dirs.items()):
        if dir_name == ".":
            continue
        lines.append(f"        {dir_name}")
        for file_path in dir_files[:5]:
            file_name = Path(file_path).stem
            lines.append(f"            {file_name}")

    return "\n".join(lines)
