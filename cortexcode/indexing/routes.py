import re
from typing import Any


def extract_api_routes(source: str, ext: str) -> list[dict[str, Any]]:
    if ext in (".js", ".jsx", ".ts", ".tsx"):
        return extract_js_routes_from_source(source)
    if ext == ".py":
        return extract_python_routes_from_source(source)
    if ext == ".java":
        return extract_java_routes_from_source(source)
    return []


def extract_js_routes_from_source(source: str) -> list[dict[str, Any]]:
    route_keys = set()
    route_defs: list[dict[str, Any]] = []
    patterns = [
        (re.compile(r'router\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']', re.IGNORECASE), "express", None),
        (re.compile(r'app\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']', re.IGNORECASE), "express", None),
        (re.compile(r'@Get\(\s*["\']([^"\']+)["\']\s*\)'), "nestjs", "GET"),
        (re.compile(r'@Post\(\s*["\']([^"\']+)["\']\s*\)'), "nestjs", "POST"),
        (re.compile(r'@Put\(\s*["\']([^"\']+)["\']\s*\)'), "nestjs", "PUT"),
        (re.compile(r'@Delete\(\s*["\']([^"\']+)["\']\s*\)'), "nestjs", "DELETE"),
        (re.compile(r'@Patch\(\s*["\']([^"\']+)["\']\s*\)'), "nestjs", "PATCH"),
    ]

    for pattern, framework, fixed_method in patterns:
        for match in pattern.finditer(source):
            if fixed_method:
                method = fixed_method
                path = match.group(1)
            else:
                method = match.group(1).upper()
                path = match.group(2)
            key = (framework, method, path)
            if key not in route_keys:
                route_keys.add(key)
                route_defs.append({"method": method, "path": path, "framework": framework})

    return route_defs


def find_js_routes_recursive(node: Any, routes: list[dict[str, Any]]) -> None:
    source_bytes = node.text if hasattr(node, 'text') else b''
    source_str = source_bytes.decode("utf-8", errors="ignore")

    patterns = [
        (r'["\'](GET|POST|PUT|DELETE|PATCH)\s+["\']([^"\']+)["\']', 'express'),
        (r'@Get\(["\']([^"\']+)["\']\)', 'nestjs'),
        (r'@Post\(["\']([^"\']+)["\']\)', 'nestjs'),
        (r'@Put\(["\']([^"\']+)["\']\)', 'nestjs'),
        (r'@Delete\(["\']([^"\']+)["\']\)', 'nestjs'),
        (r'@RequestMapping\(["\']([^"\']+)["\']', 'spring'),
        (r'router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', 'express'),
        (r'app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', 'express'),
    ]

    for pattern, framework in patterns:
        matches = re.findall(pattern, source_str)
        for match in matches:
            if len(match) == 2:
                method = match[0] if match[0] in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'] else framework
                path = match[1] if match[0] in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'] else match[1]
                routes.append({"method": method.upper(), "path": path, "framework": framework})

    for child in node.children:
        find_js_routes_recursive(child, routes)


def extract_python_routes_from_source(source: str) -> list[dict[str, Any]]:
    route_keys = set()
    route_defs: list[dict[str, Any]] = []
    decorator_patterns = [
        (re.compile(r'@(app|router|blueprint)\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']', re.IGNORECASE), None),
        (re.compile(r'@(app|router|blueprint)\.route\(\s*["\']([^"\']+)["\'](?:\s*,\s*methods\s*=\s*\[([^\]]+)\])?', re.IGNORECASE), "route"),
    ]

    for pattern, mode in decorator_patterns:
        for match in pattern.finditer(source):
            if mode == "route":
                path = match.group(2)
                methods_clause = match.group(3) or "GET"
                methods = re.findall(r'(GET|POST|PUT|DELETE|PATCH)', methods_clause, flags=re.IGNORECASE) or ["GET"]
                for method in methods:
                    key = ("python", method.upper(), path)
                    if key not in route_keys:
                        route_keys.add(key)
                        route_defs.append({"method": method.upper(), "path": path, "framework": "python"})
            else:
                method = match.group(2).upper()
                path = match.group(3)
                key = ("python", method, path)
                if key not in route_keys:
                    route_keys.add(key)
                    route_defs.append({"method": method, "path": path, "framework": "python"})

    return route_defs


def extract_java_routes_from_source(source: str) -> list[dict[str, Any]]:
    route_keys = set()
    route_defs: list[dict[str, Any]] = []
    patterns = [
        (re.compile(r'@GetMapping\(\s*["\']([^"\']+)["\']\s*\)'), "GET"),
        (re.compile(r'@PostMapping\(\s*["\']([^"\']+)["\']\s*\)'), "POST"),
        (re.compile(r'@PutMapping\(\s*["\']([^"\']+)["\']\s*\)'), "PUT"),
        (re.compile(r'@DeleteMapping\(\s*["\']([^"\']+)["\']\s*\)'), "DELETE"),
        (re.compile(r'@PatchMapping\(\s*["\']([^"\']+)["\']\s*\)'), "PATCH"),
    ]

    for pattern, method in patterns:
        for match in pattern.finditer(source):
            path = match.group(1)
            key = ("spring", method, path)
            if key not in route_keys:
                route_keys.add(key)
                route_defs.append({"method": method, "path": path, "framework": "spring"})

    return route_defs
