from pathlib import Path
from typing import Any


def get_max_file_size(filter_opts: dict[str, Any], root: Path) -> int:
    configured_max_size = filter_opts.get("max_file_size")
    if configured_max_size is not None:
        try:
            return int(configured_max_size)
        except (TypeError, ValueError):
            pass

    try:
        config_file = root / ".cortexcode.yaml"
        if config_file.exists():
            import yaml

            data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
            if data and "indexer" in data:
                return data["indexer"].get("max_file_size", 1024 * 1024)
    except Exception:
        pass

    return 1024 * 1024
