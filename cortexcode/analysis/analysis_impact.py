from typing import Any


def analyze_change_impact(index: dict, symbol_name: str) -> dict[str, Any]:
    """Analyze what would be impacted if a symbol is changed.

    Returns:
    - direct_callers: symbols that call this one
    - indirect_callers: symbols that call the direct callers (2nd-degree)
    - affected_files: files containing affected symbols
    - affected_tests: test files that may need updating
    """
    call_graph = index.get("call_graph", {})
    files = index.get("files", {})

    reverse_graph: dict[str, set[str]] = {}
    for caller, callees in call_graph.items():
        for callee in callees:
            if callee not in reverse_graph:
                reverse_graph[callee] = set()
            reverse_graph[callee].add(caller)

    direct_callers = list(reverse_graph.get(symbol_name, set()))

    indirect_callers = set()
    for direct_caller in direct_callers:
        for caller in reverse_graph.get(direct_caller, set()):
            if caller != symbol_name and caller not in direct_callers:
                indirect_callers.add(caller)

    sym_to_file: dict[str, str] = {}
    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue
        for sym in file_data.get("symbols", []):
            sym_to_file[sym.get("name", "")] = rel_path

    all_affected = {symbol_name} | set(direct_callers) | indirect_callers
    affected_files = set()
    for sym in all_affected:
        if sym in sym_to_file:
            affected_files.add(sym_to_file[sym])

    affected_tests = [path for path in affected_files if "test" in path.lower() or "spec" in path.lower()]
    non_test_files = [path for path in affected_files if path not in affected_tests]

    file_deps = index.get("file_dependencies", {})
    dep_affected = set()
    for file_path, deps in file_deps.items():
        if any(affected_file in deps for affected_file in non_test_files):
            dep_affected.add(file_path)

    return {
        "symbol": symbol_name,
        "direct_callers": sorted(direct_callers),
        "indirect_callers": sorted(indirect_callers),
        "affected_files": sorted(non_test_files),
        "affected_tests": sorted(affected_tests),
        "importing_files": sorted(dep_affected - affected_files),
        "total_impact": len(all_affected) - 1,
        "risk": "high" if len(all_affected) > 10 else "medium" if len(all_affected) > 3 else "low",
    }
