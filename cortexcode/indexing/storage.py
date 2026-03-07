import json
from pathlib import Path
from typing import Any


def save_index(index: dict[str, Any], output_path: Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=2), encoding="utf-8")


def load_index(index_path: Path) -> dict[str, Any]:
    return json.loads(Path(index_path).read_text(encoding="utf-8"))
