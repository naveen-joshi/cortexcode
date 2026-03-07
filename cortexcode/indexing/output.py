import hashlib
from datetime import datetime, timezone
from pathlib import Path


def timestamp_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_hashes(root: Path, file_symbols: dict[str, object]) -> dict[str, str]:
    hashes = {}
    for rel_path in file_symbols:
        file_path = root / rel_path
        try:
            content = file_path.read_bytes()
            hashes[rel_path] = hashlib.sha256(content).hexdigest()
        except OSError:
            pass
    return hashes
