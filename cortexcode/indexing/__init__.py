from cortexcode.indexing.build import build_index_result
from cortexcode.indexing.calls import find_calls_recursive
from cortexcode.indexing.config import get_max_file_size
from cortexcode.indexing.dispatch import extract_symbols_by_extension
from cortexcode.indexing.extensions import get_all_extensions
from cortexcode.indexing.filtering import is_file_too_large, should_ignore_file
from cortexcode.indexing.gitignore import load_gitignore_patterns, match_pattern, matches_gitignore
from cortexcode.indexing.incremental import load_previous_index_data, reuse_unchanged_file
from cortexcode.indexing.nodes import get_node_name
from cortexcode.indexing.output import compute_hashes, timestamp_now
from cortexcode.indexing.parsers import get_parser_for_extension
from cortexcode.indexing.params import extract_params
from cortexcode.indexing.pipeline import index_file, merge_indexed_file
from cortexcode.indexing.profile import build_project_profile
from cortexcode.indexing.resolution import build_file_dependencies, build_type_map
from cortexcode.indexing.session import prepare_indexing_session
from cortexcode.indexing.storage import load_index, save_index
from cortexcode.indexing.walk import walk_and_index_files
from cortexcode.indexing.imports_exports import extract_exports, extract_imports
from cortexcode.indexing.routes import find_js_routes_recursive
from cortexcode.indexing.metadata import extract_decorators, extract_docstring, extract_jsdoc, extract_modifiers, extract_return_type

__all__ = [
    "build_index_result",
    "build_project_profile",
    "build_file_dependencies",
    "build_type_map",
    "get_max_file_size",
    "get_all_extensions",
    "extract_symbols_by_extension",
    "should_ignore_file",
    "is_file_too_large",
    "load_gitignore_patterns",
    "match_pattern",
    "matches_gitignore",
    "load_previous_index_data",
    "reuse_unchanged_file",
    "get_parser_for_extension",
    "index_file",
    "merge_indexed_file",
    "prepare_indexing_session",
    "walk_and_index_files",
    "find_js_routes_recursive",
    "find_calls_recursive",
    "get_node_name",
    "timestamp_now",
    "compute_hashes",
    "save_index",
    "load_index",
    "extract_params",
    "extract_imports",
    "extract_exports",
    "extract_docstring",
    "extract_decorators",
    "extract_return_type",
    "extract_modifiers",
    "extract_jsdoc",
]
