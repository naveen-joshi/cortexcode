"""Advanced analysis modules."""

from cortexcode.advanced_analysis.advanced_analysis_cycles import detect_circular_deps
from cortexcode.advanced_analysis.advanced_analysis_docs import generate_api_docs
from cortexcode.advanced_analysis.advanced_analysis_duplicates import detect_duplicates
from cortexcode.advanced_analysis.advanced_analysis_endpoints import extract_endpoints
from cortexcode.advanced_analysis.advanced_analysis_search import fuzzy_search, regex_search
from cortexcode.advanced_analysis.advanced_analysis_security import security_scan

__all__ = [
    "detect_circular_deps",
    "generate_api_docs",
    "detect_duplicates",
    "extract_endpoints",
    "fuzzy_search",
    "regex_search",
    "security_scan",
]
