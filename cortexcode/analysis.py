"""Code analysis — dead code detection, complexity metrics, and change impact analysis."""

import re
from pathlib import Path
from typing import Any


def detect_dead_code(index: dict) -> list[dict[str, Any]]:
    """Find symbols that are defined but never called by any other symbol.
    
    Returns a list of potentially dead symbols with their details.
    """
    call_graph = index.get("call_graph", {})
    files = index.get("files", {})
    
    # Build set of all called names (flatten call graph values)
    all_called: set[str] = set()
    for callees in call_graph.values():
        all_called.update(callees)
    
    # Also gather names referenced in imports across files
    all_imported: set[str] = set()
    for file_data in files.values():
        if not isinstance(file_data, dict):
            continue
        for imp in file_data.get("imports", []):
            all_imported.update(imp.get("imported", []))
    
    all_referenced = all_called | all_imported
    
    # Collect all defined symbols
    dead: list[dict[str, Any]] = []
    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue
        for sym in file_data.get("symbols", []):
            name = sym.get("name", "")
            sym_type = sym.get("type", "")
            
            # Skip entry points, constructors, overrides, test helpers
            if _is_likely_entrypoint(name, sym, rel_path):
                continue
            
            # Check if never referenced
            if name not in all_referenced:
                dead.append({
                    "name": name,
                    "type": sym_type,
                    "file": rel_path,
                    "line": sym.get("line", 0),
                    "framework": sym.get("framework"),
                    "reason": "never called or imported by any other symbol",
                })
    
    return dead


def _is_likely_entrypoint(name: str, sym: dict, file_path: str) -> bool:
    """Check if a symbol is likely an entry point that won't appear in call graph."""
    # Framework entry points
    fw = sym.get("framework") or ""
    if fw:
        return True  # Framework-detected symbols are likely wired by the framework
    
    # Common entry point patterns
    entrypoint_names = {
        "main", "app", "init", "__init__", "setup", "configure", "register",
        "run", "start", "bootstrap", "index", "default", "handler",
    }
    if name.lower() in entrypoint_names:
        return True
    
    # Exported symbols (they may be used externally)
    if sym.get("type") == "class":
        return True  # Classes are often instantiated dynamically
    
    # Test files
    if "test" in file_path.lower() or "spec" in file_path.lower():
        return True
    
    # Lifecycle methods
    lifecycle = {
        "componentDidMount", "componentWillUnmount", "render", "build",
        "ngOnInit", "ngOnDestroy", "viewDidLoad", "viewWillAppear",
        "onCreate", "onStart", "onResume", "onPause", "onStop", "onDestroy",
        "initState", "dispose", "didChangeDependencies",
    }
    if name in lifecycle:
        return True
    
    # Dunder methods
    if name.startswith("__") and name.endswith("__"):
        return True
    
    # Decorator-based routing (likely registered by framework)
    if name.startswith("get_") or name.startswith("post_") or name.startswith("handle_"):
        return True
    
    return False


def compute_complexity(index: dict, project_root: str | None = None) -> list[dict[str, Any]]:
    """Compute complexity metrics for all functions/methods.
    
    Metrics:
    - lines: approximate line count of the function body
    - params: number of parameters
    - calls: number of outgoing calls
    - cyclomatic: estimated cyclomatic complexity (branch count + 1)
    - nesting: max nesting depth estimate
    """
    files = index.get("files", {})
    results: list[dict[str, Any]] = []
    root = Path(project_root) if project_root else None
    
    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue
        
        symbols = file_data.get("symbols", [])
        
        # Try to read source for line-level analysis
        source_lines: list[str] | None = None
        if root:
            try:
                source_lines = (root / rel_path).read_text(encoding="utf-8").split("\n")
            except (OSError, UnicodeDecodeError):
                pass
        
        for sym in symbols:
            if sym.get("type") not in ("function", "method"):
                continue
            
            name = sym.get("name", "")
            line = sym.get("line", 0)
            params = sym.get("params", [])
            calls = sym.get("calls", [])
            
            metrics = {
                "name": name,
                "type": sym.get("type"),
                "file": rel_path,
                "line": line,
                "params_count": len(params),
                "calls_count": len(calls),
            }
            
            if source_lines and line > 0:
                body_lines, cyclomatic, nesting = _analyze_function_body(source_lines, line - 1)
                metrics["lines"] = body_lines
                metrics["cyclomatic"] = cyclomatic
                metrics["max_nesting"] = nesting
            
            # Compute a simple complexity score (0-100)
            score = _complexity_score(metrics)
            metrics["score"] = score
            metrics["rating"] = "low" if score < 20 else "medium" if score < 50 else "high" if score < 80 else "critical"
            
            results.append(metrics)
    
    # Sort by score descending
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results


def _analyze_function_body(lines: list[str], start_idx: int) -> tuple[int, int, int]:
    """Analyze function body for line count, cyclomatic complexity, and nesting depth.
    
    Returns: (line_count, cyclomatic_complexity, max_nesting_depth)
    """
    # Branch keywords that increase cyclomatic complexity
    branch_re = re.compile(
        r'\b(if|elif|else if|for|while|catch|except|case|&&|\|\||and |or |when)\b'
    )
    
    # Find the end of the function by tracking indentation / braces
    start_line = lines[start_idx] if start_idx < len(lines) else ""
    start_indent = len(start_line) - len(start_line.lstrip())
    
    body_lines = 0
    branch_count = 0
    max_nesting = 0
    brace_depth = 0
    indent_based = "def " in start_line or start_line.strip().endswith(":")
    
    for i in range(start_idx + 1, min(start_idx + 500, len(lines))):
        line = lines[i]
        stripped = line.strip()
        
        if not stripped or stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
            continue
        
        if indent_based:
            # Python-style: end when we see a line at same or lower indent
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= start_indent and stripped and not stripped.startswith((")", "]", "}")):
                break
            nesting = (current_indent - start_indent) // 4
        else:
            # Brace-style
            brace_depth += stripped.count("{") - stripped.count("}")
            if brace_depth <= 0 and body_lines > 0:
                break
            nesting = brace_depth
        
        body_lines += 1
        max_nesting = max(max_nesting, nesting)
        branch_count += len(branch_re.findall(stripped))
    
    cyclomatic = branch_count + 1
    return body_lines, cyclomatic, max_nesting


def _complexity_score(metrics: dict) -> int:
    """Compute a 0-100 complexity score from metrics."""
    score = 0.0
    
    # Line count (0-30 points)
    body_lines = metrics.get("lines", 0)
    if body_lines > 100:
        score += 30
    elif body_lines > 50:
        score += 20
    elif body_lines > 25:
        score += 10
    elif body_lines > 10:
        score += 5
    
    # Cyclomatic (0-30 points)
    cyclomatic = metrics.get("cyclomatic", 1)
    if cyclomatic > 20:
        score += 30
    elif cyclomatic > 10:
        score += 20
    elif cyclomatic > 5:
        score += 10
    elif cyclomatic > 3:
        score += 5
    
    # Nesting depth (0-20 points)
    nesting = metrics.get("max_nesting", 0)
    if nesting > 5:
        score += 20
    elif nesting > 3:
        score += 10
    elif nesting > 2:
        score += 5
    
    # Params count (0-10 points)
    params = metrics.get("params_count", 0)
    if params > 7:
        score += 10
    elif params > 4:
        score += 5
    
    # Calls count (0-10 points)
    calls = metrics.get("calls_count", 0)
    if calls > 15:
        score += 10
    elif calls > 8:
        score += 5
    
    return min(100, int(score))


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
    
    # Build reverse call graph: callee -> set of callers
    reverse_graph: dict[str, set[str]] = {}
    for caller, callees in call_graph.items():
        for callee in callees:
            if callee not in reverse_graph:
                reverse_graph[callee] = set()
            reverse_graph[callee].add(caller)
    
    # Direct callers
    direct_callers = list(reverse_graph.get(symbol_name, set()))
    
    # Indirect callers (2nd degree)
    indirect_callers = set()
    for dc in direct_callers:
        for caller in reverse_graph.get(dc, set()):
            if caller != symbol_name and caller not in direct_callers:
                indirect_callers.add(caller)
    
    # Build symbol -> file mapping
    sym_to_file: dict[str, str] = {}
    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue
        for sym in file_data.get("symbols", []):
            sym_to_file[sym.get("name", "")] = rel_path
    
    # Affected files
    all_affected = {symbol_name} | set(direct_callers) | indirect_callers
    affected_files = set()
    for sym in all_affected:
        if sym in sym_to_file:
            affected_files.add(sym_to_file[sym])
    
    # Test files
    affected_tests = [f for f in affected_files if "test" in f.lower() or "spec" in f.lower()]
    non_test_files = [f for f in affected_files if f not in affected_tests]
    
    # File deps that import files containing affected symbols
    file_deps = index.get("file_dependencies", {})
    dep_affected = set()
    for f, deps in file_deps.items():
        if any(af in deps for af in non_test_files):
            dep_affected.add(f)
    
    return {
        "symbol": symbol_name,
        "direct_callers": sorted(direct_callers),
        "indirect_callers": sorted(indirect_callers),
        "affected_files": sorted(non_test_files),
        "affected_tests": sorted(affected_tests),
        "importing_files": sorted(dep_affected - affected_files),
        "total_impact": len(all_affected) - 1,  # exclude self
        "risk": "high" if len(all_affected) > 10 else "medium" if len(all_affected) > 3 else "low",
    }
