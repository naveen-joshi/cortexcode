"""Performance optimization modules."""

from cortexcode.performance.performance_config import (
    DEFAULT_MAX_FILE_SIZE,
    MONOREPO_MARKERS,
    IndexStats,
    create_default_config,
    detect_monorepo,
    get_file_size_limit,
    should_skip_large_file,
)
from cortexcode.performance.performance_index_storage import compress_index, get_index_stats, load_compressed_index
from cortexcode.performance.performance_preview import parallel_index_files, preview_indexing

__all__ = [
    "DEFAULT_MAX_FILE_SIZE",
    "MONOREPO_MARKERS",
    "IndexStats",
    "detect_monorepo",
    "get_file_size_limit",
    "should_skip_large_file",
    "compress_index",
    "load_compressed_index",
    "get_index_stats",
    "preview_indexing",
    "parallel_index_files",
    "create_default_config",
]
