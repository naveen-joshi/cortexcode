from typing import Any


def detect_circular_deps(index: dict) -> list[dict[str, Any]]:
    """Detect circular dependencies in file imports and call graph."""
    results = []

    file_deps = index.get("file_dependencies", {})
    file_cycles = _find_cycles(file_deps)
    for cycle in file_cycles:
        results.append({
            "type": "file_import",
            "cycle": cycle,
            "length": len(cycle),
            "severity": "high" if len(cycle) <= 2 else "medium",
        })

    call_graph = index.get("call_graph", {})
    symbol_cycles = _find_cycles(call_graph)
    for cycle in symbol_cycles:
        if len(cycle) <= 5:
            results.append({
                "type": "call_cycle",
                "cycle": cycle,
                "length": len(cycle),
                "severity": "medium" if len(cycle) <= 2 else "low",
            })

    results.sort(key=lambda x: x["length"])
    return results


def _find_cycles(graph: dict[str, list]) -> list[list[str]]:
    """Find all cycles in a directed graph using DFS."""
    cycles = []
    visited = set()
    path = []
    path_set = set()

    def dfs(node: str):
        if node in path_set:
            idx = path.index(node)
            cycle = path[idx:] + [node]
            min_idx = cycle.index(min(cycle[:-1]))
            normalized = cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]]
            if normalized not in cycles:
                cycles.append(normalized)
            return

        if node in visited:
            return

        visited.add(node)
        path.append(node)
        path_set.add(node)

        for neighbor in graph.get(node, []):
            if neighbor in graph:
                dfs(neighbor)

        path.pop()
        path_set.discard(node)

    for node in graph:
        dfs(node)

    return cycles
