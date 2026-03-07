import re
from pathlib import Path
from typing import Any


ENDPOINT_PATTERNS = [
    (r'(?:app|router)\.(get|post|put|delete|patch|all|use)\s*\(\s*["\']([^"\']+)', "express"),
    (r'@(?:app|blueprint|bp)\.(route|get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)', "flask"),
    (r'path\s*\(\s*["\']([^"\']+)["\']', "django"),
    (r'@(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)', "fastapi"),
    (r'export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH)\s*\(', "nextjs"),
    (r'@(?:Get|Post|Put|Delete|Patch|Request)Mapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)', "spring"),
    (r'(?:Handle|HandleFunc)\s*\(\s*["\']([^"\']+)', "go-http"),
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

        if _is_nextjs_route(rel_path):
            methods = re.findall(
                r'export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s*\(',
                source,
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
            continue

        lines = source.split("\n")

        if _is_nextjs_route(rel_path):
            continue

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                continue

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

    seen = set()
    unique = []
    for endpoint in endpoints:
        key = (endpoint["method"], endpoint["path"], endpoint["file"])
        if key not in seen:
            seen.add(key)
            unique.append(endpoint)

    unique.sort(key=lambda x: (x["path"], x["method"]))

    return {
        "count": len(unique),
        "endpoints": unique,
        "frameworks": list(set(endpoint["framework"] for endpoint in unique)),
    }


def _is_nextjs_route(path: str) -> bool:
    """Check if a file is a Next.js API/app route."""
    normalized = path.replace("\\", "/")
    return (
        ("/api/" in normalized and "route." in normalized)
        or ("/app/" in normalized and "route." in normalized)
    )


def _is_inside_string(lines: list[str], line_idx: int) -> bool:
    """Check if a line is inside a string literal."""
    if line_idx < 0 or line_idx >= len(lines):
        return False

    quote_count = 0
    in_string = False
    current_quote = None

    for current_index in range(line_idx + 1):
        line = lines[current_index]
        for char in line:
            if char in ('"', "'", '`') and (current_index != line_idx or True):
                if not in_string:
                    in_string = True
                    current_quote = char
                    quote_count = 1
                elif char == current_quote:
                    if current_index == line_idx and line.index(char) > 0 and line[line.index(char) - 1] == '\\':
                        continue
                    quote_count += 1
                    if quote_count % 2 == 0:
                        in_string = False
                        current_quote = None

    return in_string


def _nextjs_file_to_route(path: str) -> str:
    """Convert Next.js file path to route path."""
    normalized = path.replace("\\", "/")
    match = re.search(r'(?:src/)?app(/.*)/route\.(?:ts|js|tsx|jsx)', normalized)
    if match:
        return match.group(1)
    match = re.search(r'pages(/.*?)\.(?:ts|js|tsx|jsx)', normalized)
    if match:
        route = match.group(1)
        if route.endswith("/index"):
            route = route[:-6] or "/"
        return route
    return normalized
