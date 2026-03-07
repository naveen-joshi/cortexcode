from pathlib import Path
from typing import Any, Callable


GetMaxFileSize = Callable[[Path], int]


def prepare_indexing_session(filter_opts: dict[str, Any], root_path: Path, get_max_file_size: GetMaxFileSize) -> dict[str, Any]:
    filter_opts = filter_opts or {}
    return {
        "filter_opts": filter_opts,
        "include_tests": filter_opts.get("include_tests", False),
        "exclude_patterns": set(filter_opts.get("exclude_patterns", [])),
        "include_patterns": filter_opts.get("include_patterns", []),
        "monorepo_root": filter_opts.get("monorepo_root"),
        "max_file_size": get_max_file_size(root_path),
        "symbols": [],
        "call_graph": {},
        "file_symbols": {},
        "parsers": {},
    }
