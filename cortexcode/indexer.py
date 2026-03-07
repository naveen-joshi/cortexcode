"""AST Indexer - Parse code files and extract symbols, calls, and relationships."""

from pathlib import Path
from typing import Any

from tree_sitter import Parser

from cortexcode.indexing.profile import (
    build_project_profile,
)
from cortexcode.indexing.build import build_index_result
from cortexcode.indexing.config import get_max_file_size
from cortexcode.indexing.defaults import DEFAULT_IGNORE_PATTERNS
from cortexcode.indexing.extensions import get_all_extensions
from cortexcode.indexing.filtering import is_file_too_large, should_ignore_file
from cortexcode.indexing.gitignore import load_gitignore_patterns, match_pattern, matches_gitignore
from cortexcode.indexing.incremental import load_previous_index_data, reuse_unchanged_file
from cortexcode.indexing.extractor_mixin import IndexerExtractorMixin
from cortexcode.indexing.languages import LANGUAGE_MAP, REGEX_LANGUAGES, SUPPORTED_EXTENSIONS
from cortexcode.indexing.output import compute_hashes, timestamp_now
from cortexcode.indexing.parsers import get_parser_for_extension
from cortexcode.indexing.pipeline import index_file, merge_indexed_file
from cortexcode.indexing.session import prepare_indexing_session
from cortexcode.indexing.walk import walk_and_index_files
from cortexcode.indexing.storage import load_index as load_index_data, save_index as save_index_data
from cortexcode.indexing.resolution import (
    build_file_dependencies,
    build_type_map,
)
from cortexcode.plugins import plugin_registry


class CodeIndexer(IndexerExtractorMixin):
    """Parse source files and extract symbols, calls, and relationships."""
    
    SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS
    
    @classmethod
    def get_all_extensions(cls) -> set[str]:
        """Get all supported extensions including plugin-registered ones."""
        return get_all_extensions(cls.SUPPORTED_EXTENSIONS, plugin_registry.registered_extensions)
    
    def __init__(self):
        self.parsers: dict[str, Parser] = {}
        self.symbols: list[dict[str, Any]] = []
        self.call_graph: dict[str, list[str]] = {}
        self.file_symbols: dict[str, list[dict[str, Any]]] = {}
        self.gitignore_patterns: list[tuple[str, bool]] = []
        
        # Filter options
        self.filter_opts = {}
        self.include_tests = False
        self.exclude_patterns = set()
        self.include_patterns = []
        self.monorepo_root = None
        self.max_file_size = 1024 * 1024
        
        self.default_ignore_patterns = DEFAULT_IGNORE_PATTERNS
    
    def _get_parser(self, ext: str) -> Parser | None:
        """Get or create a parser for the given extension."""
        return get_parser_for_extension(ext, self.parsers, LANGUAGE_MAP)
    
    def index_directory(self, root_path: Path, incremental: bool = False, filter_opts: dict = None) -> dict[str, Any]:
        """Index all supported files in a directory.
        
        Args:
            root_path: Path to index
            incremental: If True, only re-index changed files based on hash
            filter_opts: Dictionary with filtering options:
                - include_tests: bool - Include test files (default: False)
                - exclude_patterns: list - Additional patterns to exclude
                - include_patterns: list - Only include paths matching these patterns
                - monorepo_root: str - Monorepo root for nx-style projects
        """
        root_path = Path(root_path).resolve()
        session = prepare_indexing_session(filter_opts, root_path, self._get_max_file_size)
        self.filter_opts = session["filter_opts"]
        self.include_tests = session["include_tests"]
        self.exclude_patterns = session["exclude_patterns"]
        self.include_patterns = session["include_patterns"]
        self.monorepo_root = session["monorepo_root"]
        self.max_file_size = session["max_file_size"]

        self.symbols = session["symbols"]
        self.call_graph = session["call_graph"]
        self.file_symbols = session["file_symbols"]
        self.parsers = session["parsers"]
        
        self._load_gitignore(root_path)
        
        # Load plugins from config
        plugin_config = root_path / ".cortexcode" / "plugins.json"
        plugin_registry.load_from_config(plugin_config)
        
        old_hashes, old_index_data = load_previous_index_data(root_path, incremental)

        def reuse_file(file_path: Path) -> bool:
            return reuse_unchanged_file(
                file_path,
                root_path,
                old_hashes,
                old_index_data,
                self.file_symbols,
                self.symbols,
                self.call_graph,
            )

        walk_and_index_files(
            root_path,
            self.get_all_extensions(),
            self._should_ignore,
            self._is_file_too_large,
            self.max_file_size,
            incremental,
            reuse_file,
            self._index_file,
        )
        
        return self._build_index(root_path)
    
    def _load_gitignore(self, root: Path) -> None:
        """Load all .gitignore files from root and subdirectories."""
        self.gitignore_patterns = load_gitignore_patterns(root)
    
    def _matches_gitignore(self, file_path: Path, root: Path) -> bool:
        """Check if file matches gitignore patterns."""
        return matches_gitignore(file_path, root, self.gitignore_patterns)
    
    def _match_pattern(self, pattern: str, parts: tuple, rel_str: str) -> bool:
        """Match a single gitignore pattern."""
        return match_pattern(pattern, parts, rel_str)
    
    def _should_ignore(self, file_path: Path, root: Path) -> bool:
        """Check if file should be ignored based on gitignore, defaults, and filter options."""
        return should_ignore_file(
            file_path,
            root,
            self.default_ignore_patterns,
            self.exclude_patterns,
            self.include_patterns,
            self.include_tests,
            self._matches_gitignore,
        )
    
    def _get_max_file_size(self, root: Path) -> int:
        """Get max file size from config or default."""
        return get_max_file_size(self.filter_opts, root)
    
    def _is_file_too_large(self, file_path: Path, max_size: int) -> bool:
        """Check if file exceeds size limit."""
        return is_file_too_large(file_path, max_size)
    
    def _index_file(self, file_path: Path, root: Path) -> None:
        """Index a single file."""
        result = index_file(
            file_path,
            root,
            REGEX_LANGUAGES,
            plugin_registry,
            self._get_parser,
            self._extract_regex,
            self._extract_imports_regex,
            self._extract_symbols,
            self._extract_imports,
            self._extract_exports,
            self._extract_api_routes,
            self._extract_entities,
        )
        if not result:
            return

        rel_path, file_data, symbols = result
        merge_indexed_file(
            rel_path,
            file_data,
            symbols,
            self.file_symbols,
            self.symbols,
            self.call_graph,
        )
    
    def _build_index(self, root: Path) -> dict[str, Any]:
        """Build the final index structure."""
        return build_index_result(
            root=root,
            file_symbols=self.file_symbols,
            call_graph=self.call_graph,
            timestamp=timestamp_now(),
            file_hashes=compute_hashes(root, self.file_symbols),
            build_file_dependencies_fn=lambda: build_file_dependencies(self.file_symbols),
            build_type_map_fn=lambda: build_type_map(self.file_symbols),
            build_project_profile_fn=lambda _root, file_deps: build_project_profile(self.file_symbols, self.call_graph, file_deps),
            language_map=LANGUAGE_MAP,
            regex_languages=REGEX_LANGUAGES,
            plugin_registry=plugin_registry,
        )


def index_directory(path: str | Path, incremental: bool = False, filter_opts: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convenience function to index a directory."""
    indexer = CodeIndexer()
    return indexer.index_directory(Path(path), incremental=incremental, filter_opts=filter_opts)


def save_index(index: dict[str, Any], output_path: Path) -> None:
    """Save index to JSON file."""
    save_index_data(index, output_path)


def load_index(index_path: Path) -> dict[str, Any]:
    """Load index from JSON file."""
    return load_index_data(index_path)
