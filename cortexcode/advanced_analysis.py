"""Advanced code analysis — duplication, security, circular deps, API endpoints, doc generation."""

import re
import hashlib
from pathlib import Path
from typing import Any
from difflib import SequenceMatcher


# ─── Fuzzy Search ───────────────────────────────────────────────────────────

def fuzzy_search(index: dict, query: str, threshold: float = 0.5, limit: int = 20) -> list[dict[str, Any]]:
    """Fuzzy search for symbols — finds approximate matches.
    
    Uses substring matching, case-insensitive matching, and sequence similarity.
    """
    query_lower = query.lower()
    files = index.get("files", {})
    results = []
    
    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue
        for sym in file_data.get("symbols", []):
            name = sym.get("name", "")
            name_lower = name.lower()
            
            # Exact substring match — highest score
            if query_lower in name_lower:
                score = 1.0 if query_lower == name_lower else 0.9
            else:
                # Sequence similarity
                score = SequenceMatcher(None, query_lower, name_lower).ratio()
                
                # Bonus for matching initials (e.g., "guc" matches "getUserCount")
                initials = _extract_initials(name)
                if query_lower in initials.lower():
                    score = max(score, 0.75)
                
                # Bonus for matching words (e.g., "user auth" matches "userAuthentication")
                if all(w in name_lower for w in query_lower.split()):
                    score = max(score, 0.8)
            
            if score >= threshold:
                results.append({
                    "name": name,
                    "type": sym.get("type"),
                    "file": rel_path,
                    "line": sym.get("line"),
                    "params": sym.get("params", []),
                    "doc": sym.get("doc"),
                    "score": round(score, 3),
                })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def regex_search(index: dict, pattern: str, sym_type: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """Search symbols using regex pattern."""
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return [{"error": f"Invalid regex: {e}"}]
    
    files = index.get("files", {})
    results = []
    
    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue
        for sym in file_data.get("symbols", []):
            name = sym.get("name", "")
            if regex.search(name):
                if sym_type and sym.get("type") != sym_type:
                    continue
                results.append({
                    "name": name,
                    "type": sym.get("type"),
                    "file": rel_path,
                    "line": sym.get("line"),
                    "params": sym.get("params", []),
                    "doc": sym.get("doc"),
                })
    
    return results[:limit]


def _extract_initials(name: str) -> str:
    """Extract initials from camelCase/PascalCase/snake_case name."""
    # camelCase/PascalCase: extract uppercase letters
    initials = re.findall(r'[A-Z]', name)
    if initials:
        return ''.join(initials)
    # snake_case: extract first letter of each word
    parts = name.split('_')
    return ''.join(p[0] for p in parts if p)


# ─── Code Duplication Detection ─────────────────────────────────────────────

def detect_duplicates(index: dict, project_root: str | None = None, min_lines: int = 5) -> list[dict[str, Any]]:
    """Find duplicate or very similar code blocks.
    
    Compares function bodies by normalizing whitespace and variable names,
    then computing similarity scores.
    """
    files = index.get("files", {})
    root = Path(project_root) if project_root else None
    
    # Collect all function bodies
    functions: list[dict] = []
    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue
        
        source_lines = None
        if root:
            try:
                source_lines = (root / rel_path).read_text(encoding="utf-8").split("\n")
            except (OSError, UnicodeDecodeError):
                continue
        
        if not source_lines:
            continue
        
        for sym in file_data.get("symbols", []):
            if sym.get("type") not in ("function", "method"):
                continue
            
            line = sym.get("line", 0)
            if line <= 0:
                continue
            
            body = _extract_function_body(source_lines, line - 1)
            if len(body.split("\n")) < min_lines:
                continue
            
            normalized = _normalize_code(body)
            functions.append({
                "name": sym.get("name", ""),
                "file": rel_path,
                "line": line,
                "body": body,
                "normalized": normalized,
                "hash": hashlib.md5(normalized.encode()).hexdigest(),
            })
    
    # Group by hash for exact duplicates
    hash_groups: dict[str, list] = {}
    for func in functions:
        h = func["hash"]
        if h not in hash_groups:
            hash_groups[h] = []
        hash_groups[h].append(func)
    
    duplicates = []
    seen_pairs = set()
    
    # Exact duplicates
    for h, group in hash_groups.items():
        if len(group) > 1:
            duplicates.append({
                "type": "exact",
                "similarity": 1.0,
                "functions": [
                    {"name": f["name"], "file": f["file"], "line": f["line"]}
                    for f in group
                ],
                "lines": len(group[0]["body"].split("\n")),
            })
            for f in group:
                seen_pairs.add((f["file"], f["line"]))
    
    # Near duplicates (similarity > 0.8)
    for i, f1 in enumerate(functions):
        if (f1["file"], f1["line"]) in seen_pairs:
            continue
        for f2 in functions[i + 1:]:
            if (f2["file"], f2["line"]) in seen_pairs:
                continue
            if f1["hash"] == f2["hash"]:
                continue
            
            sim = SequenceMatcher(None, f1["normalized"], f2["normalized"]).ratio()
            if sim > 0.8:
                duplicates.append({
                    "type": "near",
                    "similarity": round(sim, 3),
                    "functions": [
                        {"name": f1["name"], "file": f1["file"], "line": f1["line"]},
                        {"name": f2["name"], "file": f2["file"], "line": f2["line"]},
                    ],
                    "lines": max(
                        len(f1["body"].split("\n")),
                        len(f2["body"].split("\n")),
                    ),
                })
    
    duplicates.sort(key=lambda x: x["similarity"], reverse=True)
    return duplicates


def _extract_function_body(lines: list[str], start_idx: int) -> str:
    """Extract function body from source lines."""
    if start_idx >= len(lines):
        return ""
    
    start_line = lines[start_idx]
    start_indent = len(start_line) - len(start_line.lstrip())
    indent_based = "def " in start_line or start_line.strip().endswith(":")
    
    body = [lines[start_idx]]
    brace_depth = 0
    
    for i in range(start_idx + 1, min(start_idx + 300, len(lines))):
        line = lines[i]
        stripped = line.strip()
        
        if not stripped:
            body.append(line)
            continue
        
        if indent_based:
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= start_indent and stripped and not stripped.startswith((")", "]", "}")):
                break
        else:
            brace_depth += stripped.count("{") - stripped.count("}")
            if brace_depth <= 0 and len(body) > 1:
                body.append(line)
                break
        
        body.append(line)
    
    return "\n".join(body)


def _normalize_code(code: str) -> str:
    """Normalize code for comparison — remove comments, normalize whitespace, replace identifiers."""
    lines = []
    for line in code.split("\n"):
        stripped = line.strip()
        # Remove comments
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        # Remove inline comments
        stripped = re.sub(r'#.*$', '', stripped)
        stripped = re.sub(r'//.*$', '', stripped)
        stripped = stripped.strip()
        if stripped:
            lines.append(stripped)
    
    result = "\n".join(lines)
    # Normalize string literals
    result = re.sub(r'"[^"]*"', '"STR"', result)
    result = re.sub(r"'[^']*'", "'STR'", result)
    # Normalize numbers
    result = re.sub(r'\b\d+\b', 'NUM', result)
    return result


# ─── Security Scan ──────────────────────────────────────────────────────────

SECRET_PATTERNS = [
    (r'(?:api[_-]?key|apikey)\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{16,}', "API key", "high"),
    (r'(?:secret|password|passwd|pwd)\s*[:=]\s*["\'][^"\']{4,}["\']', "Hardcoded password/secret", "critical"),
    (r'(?:token|auth[_-]?token|access[_-]?token)\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.]{16,}', "Hardcoded token", "high"),
    (r'(?:aws[_-]?access|aws[_-]?secret)\s*[:=]\s*["\']?[A-Za-z0-9/+=]{16,}', "AWS credential", "critical"),
    (r'(?:private[_-]?key|ssh[_-]?key)\s*[:=]\s*["\'].*["\']', "Private key reference", "critical"),
    (r'(?:jdbc|mongodb|mysql|postgres|redis)://[^\s"\']+', "Database connection string", "high"),
    (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API key", "critical"),
    (r'ghp_[a-zA-Z0-9]{36}', "GitHub personal access token", "critical"),
    (r'xoxb-[a-zA-Z0-9-]+', "Slack bot token", "critical"),
    (r'(?:AKIA|ASIA)[A-Z0-9]{16}', "AWS Access Key ID", "critical"),
]

SQL_INJECTION_PATTERNS = [
    (r'(?:execute|query|raw)\s*\(\s*(?:f["\']|["\'].*%|.*\.format\(|.*\+\s*(?:req|request|params|input))', "SQL injection risk — use parameterized queries", "high"),
    (r'(?:cursor\.execute|db\.query)\s*\(\s*["\'].*\{', "SQL injection risk — f-string in query", "high"),
]

XSS_PATTERNS = [
    (r'innerHTML\s*=\s*(?![\'"]\s*$)', "Potential XSS — innerHTML assignment", "medium"),
    (r'dangerouslySetInnerHTML', "Potential XSS — dangerouslySetInnerHTML", "medium"),
    (r'document\.write\s*\(', "Potential XSS — document.write", "medium"),
]

UNSAFE_PATTERNS = [
    (r'\beval\s*\(', "Unsafe eval() usage", "high"),
    (r'\bexec\s*\(', "Unsafe exec() usage", "high"),
    (r'subprocess\.(call|run|Popen)\s*\(.*shell\s*=\s*True', "Shell injection risk", "high"),
    (r'os\.system\s*\(', "Shell injection risk — os.system", "high"),
    (r'pickle\.loads?\s*\(', "Unsafe deserialization — pickle", "medium"),
    (r'yaml\.load\s*\([^)]*\)\s*$', "Unsafe YAML load (use safe_load)", "medium"),
    (r'Math\.random\(\)', "Insecure randomness — use crypto.getRandomValues", "low"),
]


def security_scan(project_root: str, index: dict | None = None) -> dict[str, Any]:
    """Scan source code for security issues."""
    root = Path(project_root)
    files = index.get("files", {}) if index else {}
    
    findings: list[dict] = []
    scanned_files = 0
    
    # Get file list from index or scan directory
    file_paths = []
    if files:
        for rel_path in files:
            file_paths.append(root / rel_path)
    else:
        exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".php"}
        for ext in exts:
            file_paths.extend(root.rglob(f"*{ext}"))
    
    all_patterns = (
        [(p, d, s, "secret") for p, d, s in SECRET_PATTERNS] +
        [(p, d, s, "sql_injection") for p, d, s in SQL_INJECTION_PATTERNS] +
        [(p, d, s, "xss") for p, d, s in XSS_PATTERNS] +
        [(p, d, s, "unsafe_code") for p, d, s in UNSAFE_PATTERNS]
    )
    compiled = [(re.compile(p, re.IGNORECASE), d, s, c) for p, d, s, c in all_patterns]
    
    for file_path in file_paths:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        
        scanned_files += 1
        rel = str(file_path.relative_to(root))
        
        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
                continue
            # Skip test files for some checks
            is_test = "test" in rel.lower() or "spec" in rel.lower()
            
            for regex, desc, severity, category in compiled:
                if is_test and category in ("unsafe_code",):
                    continue
                if regex.search(line):
                    findings.append({
                        "file": rel,
                        "line": line_num,
                        "category": category,
                        "severity": severity,
                        "description": desc,
                        "snippet": stripped[:120],
                    })
    
    # Deduplicate
    seen = set()
    unique_findings = []
    for f in findings:
        key = (f["file"], f["line"], f["category"])
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)
    
    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    unique_findings.sort(key=lambda x: severity_order.get(x["severity"], 99))
    
    summary = {}
    for f in unique_findings:
        cat = f["category"]
        summary[cat] = summary.get(cat, 0) + 1
    
    return {
        "scanned_files": scanned_files,
        "total_findings": len(unique_findings),
        "summary": summary,
        "severity_counts": {
            s: sum(1 for f in unique_findings if f["severity"] == s)
            for s in ("critical", "high", "medium", "low")
        },
        "findings": unique_findings,
    }


# ─── Circular Dependency Detection ──────────────────────────────────────────

def detect_circular_deps(index: dict) -> list[dict[str, Any]]:
    """Detect circular dependencies in file imports and call graph."""
    results = []
    
    # File-level circular dependencies
    file_deps = index.get("file_dependencies", {})
    file_cycles = _find_cycles(file_deps)
    for cycle in file_cycles:
        results.append({
            "type": "file_import",
            "cycle": cycle,
            "length": len(cycle),
            "severity": "high" if len(cycle) <= 2 else "medium",
        })
    
    # Symbol-level circular calls
    call_graph = index.get("call_graph", {})
    symbol_cycles = _find_cycles(call_graph)
    for cycle in symbol_cycles:
        if len(cycle) <= 5:  # Only report short cycles
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
            # Found a cycle — extract it
            idx = path.index(node)
            cycle = path[idx:] + [node]
            # Normalize cycle so smallest element is first
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
            if neighbor in graph:  # Only follow edges to known nodes
                dfs(neighbor)
        
        path.pop()
        path_set.discard(node)
    
    for node in graph:
        dfs(node)
    
    return cycles


# ─── API Endpoint Extraction ────────────────────────────────────────────────

ENDPOINT_PATTERNS = [
    # Express.js
    (r'(?:app|router)\.(get|post|put|delete|patch|all|use)\s*\(\s*["\']([^"\']+)', "express"),
    # Flask
    (r'@(?:app|blueprint|bp)\.(route|get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)', "flask"),
    # Django
    (r'path\s*\(\s*["\']([^"\']+)["\']', "django"),
    # FastAPI
    (r'@(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)', "fastapi"),
    # Next.js API routes (file-based)
    (r'export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH)\s*\(', "nextjs"),
    # Spring Boot
    (r'@(?:Get|Post|Put|Delete|Patch|Request)Mapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)', "spring"),
    # Go net/http
    (r'(?:Handle|HandleFunc)\s*\(\s*["\']([^"\']+)', "go-http"),
    # Ruby on Rails
    (r'(?:get|post|put|patch|delete)\s+["\']([^"\']+)', "rails"),
]


def extract_endpoints(index: dict, project_root: str | None = None) -> dict[str, Any]:
    """Extract API endpoints from source code."""
    root = Path(project_root) if project_root else None
    files = index.get("files", {})
    
    endpoints: list[dict] = []
    seen = set()
    
    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue
        
        source = None
        if root:
            try:
                source = (root / rel_path).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
        
        if not source:
            continue
        
        # Next.js file-based routing (file path based)
        if _is_nextjs_route(rel_path):
            methods = re.findall(
                r'export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s*\(',
                source
            )
            route_path = _nextjs_file_to_route(rel_path)
            for method in methods:
                key = (method.upper(), route_path, rel_path)
                if key not in seen:
                    seen.add(key)
                    endpoints.append({
                        "method": method.upper(),
                        "path": route_path,
                        "file": rel_path,
                        "framework": "nextjs",
                    })
            continue  # Skip pattern matching for Next.js route files
        
        # Pattern-based extraction - only match at line start (not inside strings)
        lines = source.split("\n")
        
        # Skip Next.js route files (already handled above)
        if _is_nextjs_route(rel_path):
            continue
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                continue
            
            # Only match patterns at the start of a line (after optional whitespace)
            # This avoids matching strings inside code
            
            # Express.js: app.get("/path", ...) - must start with app or router
            if stripped.startswith("app.") or stripped.startswith("router."):
                match = re.search(r'\.(get|post|put|delete|patch|all|use)\s*\(\s*["\']([^"\']+)', line)
                if match:
                    method = match.group(1).upper()
                    path = match.group(2)
                    key = (method, path, rel_path)
                    if key not in seen:
                        seen.add(key)
                        endpoints.append({
                            "method": method,
                            "path": path,
                            "file": rel_path,
                            "line": line_num,
                            "framework": "express",
                        })
                    continue
            
            # Flask/FastAPI: @app.route or @app.get - must start with @
            if stripped.startswith("@"):
                match = re.search(r'@(?:app|blueprint|bp)\.(route|get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)', line)
                if match:
                    method = match.group(1).upper()
                    if method == "ROUTE":
                        method = "GET"
                    path = match.group(2)
                    key = (method, path, rel_path)
                    if key not in seen:
                        seen.add(key)
                        endpoints.append({
                            "method": method,
                            "path": path,
                            "file": rel_path,
                            "line": line_num,
                            "framework": "flask",
                        })
                    continue
                
                # Django: path( - must start with path(
                if "path(" in stripped:
                    match = re.search(r'path\s*\(\s*["\']([^"\']+)["\']', line)
                    if match:
                        path = match.group(1)
                        key = ("GET", path, rel_path)
                        if key not in seen:
                            seen.add(key)
                            endpoints.append({
                                "method": "GET",
                                "path": path,
                                "file": rel_path,
                                "line": line_num,
                                "framework": "django",
                            })
                    continue
                
                # Spring: @GetMapping, @PostMapping, etc.
                match = re.search(r'@(Get|Post|Put|Delete|Patch|Request)Mapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)', line)
                if match:
                    method = match.group(1)
                    if method == "Request":
                        method = "GET"
                    path = match.group(2)
                    key = (method, path, rel_path)
                    if key not in seen:
                        seen.add(key)
                        endpoints.append({
                            "method": method,
                            "path": path,
                            "file": rel_path,
                            "line": line_num,
                            "framework": "spring",
                        })
                    continue
    
    # Deduplicate
    seen = set()
    unique = []
    for ep in endpoints:
        key = (ep["method"], ep["path"], ep["file"])
        if key not in seen:
            seen.add(key)
            unique.append(ep)
    
    unique.sort(key=lambda x: (x["path"], x["method"]))
    
    return {
        "count": len(unique),
        "endpoints": unique,
        "frameworks": list(set(ep["framework"] for ep in unique)),
    }


def _is_nextjs_route(path: str) -> bool:
    """Check if a file is a Next.js API/app route."""
    normalized = path.replace("\\", "/")
    return (
        ("/api/" in normalized and "route." in normalized) or
        ("/app/" in normalized and "route." in normalized)
    )


def _is_inside_string(lines: list[str], line_idx: int) -> bool:
    """Check if a line is inside a string literal."""
    if line_idx < 0 or line_idx >= len(lines):
        return False
    
    # Count unescaped quotes before this line to determine if we're in a string
    quote_count = 0
    in_string = False
    current_quote = None
    
    for i in range(line_idx + 1):
        line = lines[i]
        for char in line:
            if char in ('"', "'", '`') and (i != line_idx or True):
                if not in_string:
                    in_string = True
                    current_quote = char
                    quote_count = 1
                elif char == current_quote:
                    # Check for escaped quote
                    if i == line_idx and line.index(char) > 0 and line[line.index(char) - 1] == '\\':
                        continue
                    quote_count += 1
                    if quote_count % 2 == 0:
                        in_string = False
                        current_quote = None
    
    return in_string


def _nextjs_file_to_route(path: str) -> str:
    """Convert Next.js file path to route path."""
    normalized = path.replace("\\", "/")
    # src/app/api/users/route.ts -> /api/users
    match = re.search(r'(?:src/)?app(/.*)/route\.(?:ts|js|tsx|jsx)', normalized)
    if match:
        return match.group(1)
    # pages/api/users.ts -> /api/users
    match = re.search(r'pages(/.*?)\.(?:ts|js|tsx|jsx)', normalized)
    if match:
        route = match.group(1)
        if route.endswith("/index"):
            route = route[:-6] or "/"
        return route
    return normalized


# ─── Auto-Generate API Docs ─────────────────────────────────────────────────

def generate_api_docs(index: dict, project_root: str | None = None) -> dict[str, Any]:
    """Generate API documentation from function signatures and docstrings."""
    files = index.get("files", {})
    root = Path(project_root) if project_root else None
    
    modules: list[dict] = []
    
    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue
        
        symbols = file_data.get("symbols", [])
        if not symbols:
            continue
        
        # Read source for docstrings
        source_lines = None
        if root:
            try:
                source_lines = (root / rel_path).read_text(encoding="utf-8").split("\n")
            except (OSError, UnicodeDecodeError):
                pass
        
        classes = []
        functions = []
        
        for sym in symbols:
            name = sym.get("name", "")
            sym_type = sym.get("type", "")
            line = sym.get("line", 0)
            params = sym.get("params", [])
            doc = sym.get("doc", "")
            
            # Try to extract docstring from source
            if not doc and source_lines and line > 0:
                doc = _extract_docstring(source_lines, line - 1)
            
            entry = {
                "name": name,
                "type": sym_type,
                "line": line,
                "params": params,
                "doc": doc or "",
                "calls": sym.get("calls", []),
                "framework": sym.get("framework"),
            }
            
            if sym_type == "class":
                classes.append(entry)
            elif sym_type in ("function", "method"):
                functions.append(entry)
        
        if classes or functions:
            modules.append({
                "file": rel_path,
                "classes": classes,
                "functions": functions,
                "imports": file_data.get("imports", []),
            })
    
    # Compute summary stats
    total_documented = sum(
        1 for m in modules
        for f in m["functions"] + m["classes"]
        if f["doc"]
    )
    total_symbols = sum(
        len(m["functions"]) + len(m["classes"])
        for m in modules
    )
    
    return {
        "modules": modules,
        "total_modules": len(modules),
        "total_symbols": total_symbols,
        "documented": total_documented,
        "undocumented": total_symbols - total_documented,
        "coverage_pct": round(total_documented / max(total_symbols, 1) * 100, 1),
    }


def _extract_docstring(lines: list[str], start_idx: int) -> str:
    """Extract docstring from the line after a function/class definition."""
    # Look at next few lines for a docstring
    for i in range(start_idx + 1, min(start_idx + 5, len(lines))):
        stripped = lines[i].strip()
        if not stripped:
            continue
        
        # Python triple-quoted docstring
        if stripped.startswith('"""') or stripped.startswith("'''"):
            quote = stripped[:3]
            if stripped.endswith(quote) and len(stripped) > 6:
                return stripped[3:-3].strip()
            # Multi-line docstring
            doc_lines = [stripped[3:]]
            for j in range(i + 1, min(i + 20, len(lines))):
                line = lines[j].strip()
                if line.endswith(quote):
                    doc_lines.append(line[:-3])
                    return "\n".join(doc_lines).strip()
                doc_lines.append(line)
            break
        
        # JSDoc /** ... */
        if stripped.startswith("/**"):
            doc_lines = []
            for j in range(i, min(i + 20, len(lines))):
                line = lines[j].strip()
                if line.endswith("*/"):
                    line = line[:-2].strip()
                    if line.startswith("/**"):
                        line = line[3:].strip()
                    elif line.startswith("*"):
                        line = line[1:].strip()
                    if line:
                        doc_lines.append(line)
                    return "\n".join(doc_lines).strip()
                if line.startswith("/**"):
                    line = line[3:].strip()
                elif line.startswith("*"):
                    line = line[1:].strip()
                if line:
                    doc_lines.append(line)
            break
        
        break
    
    return ""
