"""Code analysis modules."""

from cortexcode.analysis.analysis_complexity import compute_complexity
from cortexcode.analysis.analysis_dead_code import detect_dead_code
from cortexcode.analysis.analysis_impact import analyze_change_impact

__all__ = [
    "detect_dead_code",
    "compute_complexity",
    "analyze_change_impact",
]
