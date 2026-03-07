from typing import Any

from cortexcode.indexing.calls import find_calls_recursive
from cortexcode.indexing.dispatch import extract_symbols_by_extension
from cortexcode.indexing.entities import extract_entities, find_js_entities, find_python_entities
from cortexcode.indexing.extractors.csharp import extract_csharp_with_framework
from cortexcode.indexing.extractors.dart import (
    detect_dart_framework,
    extract_dart_calls,
    extract_dart_params,
    extract_dart_regex,
    extract_imports_regex,
)
from cortexcode.indexing.extractors.generic import extract_generic
from cortexcode.indexing.extractors.java import extract_java_with_framework
from cortexcode.indexing.extractors.javascript import extract_js_ts_generic
from cortexcode.indexing.extractors.kotlin import extract_kotlin_recursive
from cortexcode.indexing.extractors.swift import extract_swift_recursive
from cortexcode.indexing.frameworks import (
    detect_class_framework,
    detect_csharp_framework,
    detect_framework,
    detect_java_framework,
    detect_kotlin_framework,
    detect_swift_framework,
)
from cortexcode.indexing.imports_exports import (
    extract_exports,
    extract_imports,
    extract_python_imports_from_source,
    find_js_exports,
    find_js_imports,
    find_python_exports,
    find_python_imports,
)
from cortexcode.indexing.metadata import (
    extract_decorators,
    extract_docstring,
    extract_jsdoc,
    extract_modifiers,
    extract_return_type,
)
from cortexcode.indexing.nodes import get_node_name
from cortexcode.indexing.params import extract_params
from cortexcode.indexing.routes import (
    extract_api_routes,
    extract_java_routes_from_source,
    extract_js_routes_from_source,
    extract_python_routes_from_source,
    find_js_routes_recursive,
)


class IndexerExtractorMixin:
    """Shared symbol, import/export, route, and entity extraction helpers for CodeIndexer."""

    def _extract_symbols(self, source: str, node, ext: str) -> list[dict[str, Any]]:
        """Extract all symbols from AST based on language."""
        return extract_symbols_by_extension(
            source,
            node,
            ext,
            self._extract_python,
            self._extract_javascript,
            self._extract_typescript,
            self._extract_go,
            self._extract_rust,
            self._extract_java,
            self._extract_csharp,
            self._extract_kotlin,
            self._extract_swift,
        )

    def _extract_python(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract Python symbols."""
        self._extract_generic(source, node, symbols, current_class, "function_definition", "class_definition")

    def _extract_javascript(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract JavaScript/React symbols."""
        self._extract_js_ts_generic(source, node, symbols, current_class, is_ts=False)

    def _extract_typescript(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract TypeScript/Angular/Next.js symbols."""
        self._extract_js_ts_generic(source, node, symbols, current_class, is_ts=True)

    def _extract_js_ts_generic(self, source: str, node, symbols: list, current_class: str | None, is_ts: bool) -> None:
        """Extract JavaScript/TypeScript with framework support."""
        extract_js_ts_generic(
            source,
            node,
            symbols,
            current_class,
            is_ts,
            self._get_node_name,
            self._extract_params,
            self._extract_calls,
            self._extract_return_type,
            self._extract_jsdoc,
            self._detect_framework,
            self._detect_class_framework,
        )

    def _detect_framework(self, name: str, node, source: str) -> str | None:
        """Detect framework: React, React Native, Expo, Next.js, NestJS, Express, FastAPI, Django, Flask."""
        return detect_framework(name, node, source)

    def _detect_class_framework(self, name: str, node, source: str) -> str | None:
        """Detect class-level framework: Angular, React Native, NestJS, etc."""
        return detect_class_framework(name, node, source)

    def _extract_go(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract Go symbols."""
        self._extract_generic(source, node, symbols, current_class, "function_declaration", "method_declaration", "type_declaration")

    def _extract_rust(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract Rust symbols."""
        self._extract_generic(source, node, symbols, current_class, "function_item", "struct_item", "impl_item", "enum_item")

    def _extract_java(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract Java symbols with Spring Boot detection."""
        self._extract_java_with_framework(source, node, symbols, current_class)

    def _extract_java_with_framework(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract Java with Spring Boot framework detection."""
        extract_java_with_framework(
            source,
            node,
            symbols,
            current_class,
            self._get_node_name,
            self._extract_params,
            self._extract_calls,
            self._detect_java_framework,
        )

    def _detect_java_framework(self, name: str, node, source: str) -> str | None:
        """Detect Spring Boot and Android framework patterns."""
        return detect_java_framework(name, node, source)

    def _extract_csharp(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract C# with .NET framework detection."""
        self._extract_csharp_with_framework(source, node, symbols, current_class)

    def _extract_csharp_with_framework(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract C# with .NET framework detection."""
        extract_csharp_with_framework(
            source,
            node,
            symbols,
            current_class,
            self._get_node_name,
            self._extract_params,
            self._extract_calls,
            self._detect_csharp_framework,
        )

    def _detect_csharp_framework(self, name: str, node, source: str) -> str | None:
        """Detect .NET framework patterns."""
        return detect_csharp_framework(name, node, source)

    def _extract_kotlin(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract Kotlin symbols with Android framework detection."""
        self._extract_kotlin_recursive(source, node, symbols, current_class)

    def _extract_kotlin_recursive(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Recursively extract Kotlin symbols."""
        extract_kotlin_recursive(
            source,
            node,
            symbols,
            current_class,
            self._get_node_name,
            self._extract_params,
            self._extract_calls,
            self._detect_kotlin_framework,
        )

    def _detect_kotlin_framework(self, name: str, node, source: str) -> str | None:
        """Detect Android/Compose/Ktor framework patterns in Kotlin."""
        return detect_kotlin_framework(name, node, source)

    def _extract_swift(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract Swift symbols with iOS framework detection."""
        self._extract_swift_recursive(source, node, symbols, current_class)

    def _extract_swift_recursive(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Recursively extract Swift symbols."""
        extract_swift_recursive(
            source,
            node,
            symbols,
            current_class,
            self._get_node_name,
            self._extract_params,
            self._extract_calls,
            self._detect_swift_framework,
        )

    def _detect_swift_framework(self, name: str, node, source: str) -> str | None:
        """Detect iOS/SwiftUI/UIKit framework patterns."""
        return detect_swift_framework(name, node, source)

    def _extract_regex(self, source: str, ext: str, rel_path: str) -> list[dict[str, Any]]:
        """Regex-based symbol extraction for languages without tree-sitter (Dart)."""
        if ext == ".dart":
            return self._extract_dart_regex(source, rel_path)
        return []

    def _extract_dart_regex(self, source: str, rel_path: str) -> list[dict[str, Any]]:
        """Extract Dart/Flutter symbols using regex."""
        return extract_dart_regex(
            source,
            rel_path,
            self._detect_dart_framework,
            self._extract_dart_calls,
            self._extract_dart_params,
        )

    def _extract_dart_params(self, line: str) -> list[str]:
        """Extract parameters from a Dart function line."""
        return extract_dart_params(line)

    def _extract_dart_calls(self, source: str, line_idx: int) -> list[str]:
        """Extract function calls near a Dart function definition."""
        return extract_dart_calls(source, line_idx)

    def _detect_dart_framework(self, name: str, line: str, source: str) -> str | None:
        """Detect Flutter/Dart framework patterns."""
        return detect_dart_framework(name, line, source)

    def _extract_imports_regex(self, source: str, ext: str) -> list[dict]:
        """Extract imports using regex for non-tree-sitter languages."""
        return extract_imports_regex(source, ext)

    def _extract_generic(
        self,
        source: str,
        node,
        symbols: list,
        current_class: str | None,
        func_types: str,
        class_types: str,
        *extra_types: str,
    ) -> None:
        """Generic symbol extraction for multiple node types."""
        extract_generic(
            source,
            node,
            symbols,
            current_class,
            func_types,
            class_types,
            extra_types,
            self._get_node_name,
            self._extract_params,
            self._extract_calls,
            self._extract_docstring,
            self._extract_decorators,
            self._extract_return_type,
            self._extract_modifiers,
        )

    def _get_node_name(self, node, source: str) -> str | None:
        """Get name from definition node."""
        return get_node_name(node)

    def _extract_params(self, func_node, source: str, node_type: str) -> list[str]:
        """Extract function parameters."""
        return extract_params(func_node)

    def _extract_calls(self, func_node, source: str) -> list[str]:
        """Extract function calls within a function body."""
        calls = []
        self._find_calls_recursive(func_node, calls)
        return list(set(calls))

    def _find_calls_recursive(self, node, calls: list) -> None:
        """Recursively find function calls."""
        find_calls_recursive(node, calls)

    def _extract_imports(self, source: str, node, ext: str) -> list[dict[str, Any]]:
        """Extract import statements."""
        return extract_imports(source, node, ext)

    def _extract_python_imports_from_source(self, source: str) -> list[dict[str, Any]]:
        return extract_python_imports_from_source(source)

    def _find_js_imports(self, node, imports: list) -> None:
        """Find JavaScript/TypeScript imports."""
        find_js_imports(node, imports)

    def _find_python_imports(self, node, imports: list) -> None:
        """Find Python imports."""
        find_python_imports(node, imports)

    def _extract_exports(self, source: str, node, ext: str) -> list[dict[str, Any]]:
        """Extract export statements."""
        return extract_exports(source, node, ext, self._get_node_name)

    def _find_js_exports(self, node, exports: list) -> None:
        """Find JavaScript/TypeScript exports."""
        find_js_exports(node, exports, self._get_node_name)

    def _find_python_exports(self, node, exports: list) -> None:
        """Find Python __all__ exports."""
        find_python_exports(node, exports)

    def _extract_api_routes(self, source: str, node, ext: str) -> list[dict[str, Any]]:
        """Extract API routes/endpoints."""
        return extract_api_routes(source, ext)

    def _extract_js_routes_from_source(self, source: str) -> list[dict[str, Any]]:
        return extract_js_routes_from_source(source)

    def _extract_python_routes_from_source(self, source: str) -> list[dict[str, Any]]:
        return extract_python_routes_from_source(source)

    def _extract_java_routes_from_source(self, source: str) -> list[dict[str, Any]]:
        return extract_java_routes_from_source(source)

    def _find_js_routes(self, node, routes: list) -> None:
        """Find JavaScript/TypeScript API routes."""
        find_js_routes_recursive(node, routes)

    def _extract_entities(self, source: str, node, ext: str) -> list[dict[str, Any]]:
        """Extract database entities/models."""
        return extract_entities(source, node, ext, self._get_node_name)

    def _find_js_entities(self, node, entities: list, source: str) -> None:
        """Find JavaScript/TypeScript entities/models."""
        find_js_entities(node, entities, source, self._get_node_name)

    def _find_python_entities(self, node, entities: list, source: str) -> None:
        """Find Python entities/models."""
        find_python_entities(node, entities, source, self._get_node_name)

    def _extract_docstring(self, node, source: str) -> str | None:
        """Extract Python docstring from a function/class body."""
        return extract_docstring(node)

    def _extract_decorators(self, node, source: str) -> list[str]:
        """Extract decorators from a function/class."""
        return extract_decorators(node)

    def _extract_return_type(self, node, source: str) -> str | None:
        """Extract return type annotation."""
        return extract_return_type(node)

    def _extract_modifiers(self, node, source: str) -> list[str]:
        """Extract modifiers like async, static, private, public, etc."""
        return extract_modifiers(node)

    def _extract_jsdoc(self, node, source: str) -> str | None:
        """Extract JSDoc comment preceding a node."""
        return extract_jsdoc(node, source)
