"""Advanced code analysis — duplication, security, circular deps, API endpoints, doc generation."""

from cortexcode.advanced_analysis_cycles import detect_circular_deps
from cortexcode.advanced_analysis_docs import generate_api_docs
from cortexcode.advanced_analysis_duplicates import detect_duplicates
from cortexcode.advanced_analysis_endpoints import extract_endpoints
from cortexcode.advanced_analysis_search import fuzzy_search, regex_search
from cortexcode.advanced_analysis_security import security_scan


__all__ = [
    "fuzzy_search",
    "regex_search",
    "detect_duplicates",
    "security_scan",
    "detect_circular_deps",
    "extract_endpoints",
    "generate_api_docs",
]
