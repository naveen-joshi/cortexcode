"""Docs Generator - Generate project documentation from index.

This module is kept for backward compatibility.
The actual implementation has been moved to cortexcode.docs package.
"""

from cortexcode.docs import (
    generate_all_docs,
    generate_readme,
    generate_api_docs,
    generate_structure_docs,
    generate_flow_docs,
    generate_html_docs,
)

from cortexcode.docs.html_generators import (
    generate_tree_html,
    generate_symbols_html,
    generate_imports_html,
    generate_exports_html,
    generate_routes_html,
    generate_entities_html,
)

__all__ = [
    "generate_all_docs",
    "generate_readme",
    "generate_api_docs",
    "generate_structure_docs",
    "generate_flow_docs",
    "generate_html_docs",
    "generate_tree_html",
    "generate_symbols_html",
    "generate_imports_html",
    "generate_exports_html",
    "generate_routes_html",
    "generate_entities_html",
]
