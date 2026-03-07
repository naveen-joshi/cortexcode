from pathlib import Path
from typing import Any, Dict, List

from cortexcode.performance_config import get_file_size_limit, should_skip_large_file


def preview_indexing(root_path: Path, filter_opts: Dict[str, Any] = None) -> Dict[str, Any]:
    """Preview what would be indexed without actually indexing."""
    from cortexcode.indexer import CodeIndexer

    root_path = Path(root_path).resolve()
    filter_opts = filter_opts or {}

    indexer = CodeIndexer()
    indexer.filter_opts = filter_opts
    indexer.include_tests = filter_opts.get("include_tests", False)
    indexer.exclude_patterns = set(filter_opts.get("exclude_patterns", []))
    indexer.include_patterns = filter_opts.get("include_patterns", [])
    indexer.monorepo_root = filter_opts.get("monorepo_root")
    indexer.max_file_size = filter_opts.get("max_file_size", get_file_size_limit(root_path))

    indexer._load_gitignore(root_path)

    max_size = indexer.max_file_size
    files_to_index = []
    files_to_skip = []

    for ext in indexer.get_all_extensions():
        for file_path in root_path.rglob(f"*{ext}"):
            rel_path = file_path.relative_to(root_path)
            rel_str = str(rel_path)

            if should_skip_large_file(file_path, max_size):
                files_to_skip.append({"path": rel_str, "reason": "file too large"})
                continue

            if indexer._should_ignore(file_path, root_path):
                files_to_skip.append({"path": rel_str, "reason": "ignored"})
                continue

            files_to_index.append(rel_str)

    return {
        "files_to_index": len(files_to_index),
        "files_to_skip": len(files_to_skip),
        "sample_files": sorted(files_to_index)[:20],
        "skip_reasons": {
            "file_too_large": sum(1 for item in files_to_skip if item["reason"] == "file too large"),
            "ignored": sum(1 for item in files_to_skip if item["reason"] == "ignored"),
        },
    }


def parallel_index_files(
    files: List[Path],
    root_path: Path,
    max_workers: int = None,
) -> Dict[str, Any]:
    """Index files in parallel (experimental)."""
    return {"status": "sequential", "files": len(files)}
