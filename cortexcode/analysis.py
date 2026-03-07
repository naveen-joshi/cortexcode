"""Code analysis — dead code detection, complexity metrics, and change impact analysis."""

from cortexcode.analysis_complexity import compute_complexity
from cortexcode.analysis_dead_code import detect_dead_code
from cortexcode.analysis_impact import analyze_change_impact


__all__ = [
    "detect_dead_code",
    "compute_complexity",
    "analyze_change_impact",
]
