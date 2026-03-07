import gzip
import json
from pathlib import Path
from typing import Any, Dict, Optional

from cortexcode.performance_config import IndexStats


def compress_index(index_data: Dict[str, Any], output_path: Path, compress: bool = True) -> Path:
    """Save index with optional compression."""
    output_path = Path(output_path)

    if compress and output_path.suffix != ".gz":
        gz_path = Path(str(output_path) + ".gz")
        with gzip.open(gz_path, "wt", encoding="utf-8") as handle:
            json.dump(index_data, handle)
        return gz_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index_data, indent=2), encoding="utf-8")
    return output_path


def load_compressed_index(index_path: Path) -> Optional[Dict[str, Any]]:
    """Load index, handling both compressed and uncompressed."""
    index_path = Path(index_path)

    if index_path.exists():
        try:
            return json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    gz_path = Path(str(index_path) + ".gz")
    if gz_path.exists():
        try:
            with gzip.open(gz_path, "rt", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            pass

    return None


def get_index_stats(index_path: Path) -> IndexStats:
    """Get statistics about an existing index without re-indexing."""
    index_data = load_compressed_index(index_path)
    if not index_data:
        return IndexStats()

    stats = IndexStats()
    stats.last_indexed = index_data.get("last_indexed", "Unknown")

    files = index_data.get("files", {})
    stats.total_files = len(files)

    for path, data in files.items():
        symbols = data.get("symbols", []) if isinstance(data, dict) else data
        stats.total_symbols += len(symbols)

        ext = Path(path).suffix or "no extension"
        stats.file_types[ext] = stats.file_types.get(ext, 0) + 1
        stats.total_size += len(json.dumps(data))

    stats.index_size = index_data.get("index_size", 0)
    stats.languages = index_data.get("languages", {})
    return stats
