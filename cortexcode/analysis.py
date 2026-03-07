"""Code analysis — dead code detection, complexity metrics, and change impact analysis."""

from cortexcode.analysis import compute_complexity, detect_dead_code, analyze_change_impact


__all__ = [
    "detect_dead_code",
    "compute_complexity",
    "analyze_change_impact",
]
