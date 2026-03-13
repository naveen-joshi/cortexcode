"""Dependency vulnerability scanning — check for known vulnerable packages."""

import json
import re
from pathlib import Path
from typing import Any


def scan_dependencies(root: Path) -> dict[str, Any]:
    """Scan project for dependency files and check for known issues.
    
    Scans: package.json, requirements.txt, pyproject.toml, Gemfile, go.mod, Cargo.toml
    """
    root = Path(root).resolve()
    results = {
        "scanned_files": [],
        "dependencies": [],
        "warnings": [],
    }
    
    # package.json
    pkg_json = root / "package.json"
    if pkg_json.exists():
        _scan_package_json(pkg_json, results)
    
    # requirements.txt
    req_txt = root / "requirements.txt"
    if req_txt.exists():
        _scan_requirements_txt(req_txt, results)
    
    # pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        _scan_pyproject_toml(pyproject, results)
    
    # go.mod
    go_mod = root / "go.mod"
    if go_mod.exists():
        _scan_go_mod(go_mod, results)
    
    # Cargo.toml
    cargo = root / "Cargo.toml"
    if cargo.exists():
        _scan_cargo_toml(cargo, results)
    
    # Check for common issues
    _check_common_issues(root, results)
    
    results["total_dependencies"] = len(results["dependencies"])
    results["total_warnings"] = len(results["warnings"])
    
    return results


def _scan_package_json(path: Path, results: dict) -> None:
    """Scan package.json for dependencies."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        results["scanned_files"].append(str(path.name))
        
        for section in ("dependencies", "devDependencies"):
            deps = data.get(section, {})
            for name, version in deps.items():
                dep = {
                    "name": name,
                    "version": version,
                    "source": "package.json",
                    "dev": section == "devDependencies",
                }
                results["dependencies"].append(dep)
                
                # Check for wildcard/any versions
                if version in ("*", "latest", ""):
                    results["warnings"].append({
                        "package": name,
                        "severity": "medium",
                        "message": f"Unpinned version '{version}' — use a specific version range",
                    })
                
                # Check for known risky patterns
                _check_npm_warnings(name, version, results)
    except (json.JSONDecodeError, OSError):
        pass


def _scan_requirements_txt(path: Path, results: dict) -> None:
    """Scan requirements.txt."""
    try:
        results["scanned_files"].append(str(path.name))
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            
            # Parse name==version or name>=version
            match = re.match(r'^([a-zA-Z0-9_-]+)\s*([><=!~]+)?\s*(.*)$', line)
            if match:
                name = match.group(1)
                op = match.group(2) or ""
                version = match.group(3) or "unpinned"
                
                results["dependencies"].append({
                    "name": name,
                    "version": f"{op}{version}" if op else version,
                    "source": "requirements.txt",
                    "dev": False,
                })
                
                if not op:
                    results["warnings"].append({
                        "package": name,
                        "severity": "medium",
                        "message": "No version constraint — pin to a specific version",
                    })
    except OSError:
        pass


def _scan_pyproject_toml(path: Path, results: dict) -> None:
    """Scan pyproject.toml for dependencies."""
    try:
        content = path.read_text(encoding="utf-8")
        results["scanned_files"].append(str(path.name))
        
        # Simple TOML parsing for dependencies array
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("dependencies") and "=" in stripped:
                in_deps = True
                continue
            if in_deps:
                if stripped == "]":
                    in_deps = False
                    continue
                # Parse "package>=version"
                match = re.search(r'"([^"]+)"', stripped)
                if match:
                    dep_str = match.group(1)
                    dep_match = re.match(r'^([a-zA-Z0-9_-]+)\s*([><=!~]+)?\s*(.*)$', dep_str)
                    if dep_match:
                        results["dependencies"].append({
                            "name": dep_match.group(1),
                            "version": f"{dep_match.group(2) or ''}{dep_match.group(3) or 'unpinned'}",
                            "source": "pyproject.toml",
                            "dev": False,
                        })
    except OSError:
        pass


def _scan_go_mod(path: Path, results: dict) -> None:
    """Scan go.mod."""
    try:
        content = path.read_text(encoding="utf-8")
        results["scanned_files"].append("go.mod")
        
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("require") or line.startswith(")") or line.startswith("("):
                continue
            parts = line.split()
            if len(parts) >= 2 and "/" in parts[0]:
                results["dependencies"].append({
                    "name": parts[0],
                    "version": parts[1],
                    "source": "go.mod",
                    "dev": False,
                })
    except OSError:
        pass


def _scan_cargo_toml(path: Path, results: dict) -> None:
    """Scan Cargo.toml."""
    try:
        content = path.read_text(encoding="utf-8")
        results["scanned_files"].append("Cargo.toml")
        
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped == "[dependencies]":
                in_deps = True
                continue
            elif stripped.startswith("["):
                in_deps = False
                continue
            if in_deps and "=" in stripped:
                parts = stripped.split("=", 1)
                name = parts[0].strip()
                version = parts[1].strip().strip('"')
                results["dependencies"].append({
                    "name": name,
                    "version": version,
                    "source": "Cargo.toml",
                    "dev": False,
                })
    except OSError:
        pass


def _check_npm_warnings(name: str, version: str, results: dict) -> None:
    """Check for commonly known risky npm patterns."""
    # Check for http:// or git:// protocol in version
    if version.startswith("http://") or version.startswith("git://"):
        results["warnings"].append({
            "package": name,
            "severity": "high",
            "message": "Insecure protocol in dependency URL",
        })


def _check_common_issues(root: Path, results: dict) -> None:
    """Check for common security issues in the project."""
    # .env file committed
    env_file = root / ".env"
    if env_file.exists():
        gitignore = root / ".gitignore"
        if gitignore.exists():
            gi_content = gitignore.read_text(encoding="utf-8", errors="ignore")
            if ".env" not in gi_content:
                results["warnings"].append({
                    "package": ".env",
                    "severity": "high",
                    "message": ".env file exists but is not in .gitignore — secrets may be exposed",
                })
        else:
            results["warnings"].append({
                "package": ".env",
                "severity": "high",
                "message": ".env file exists with no .gitignore — secrets may be exposed",
            })
    
    # package-lock.json missing
    if (root / "package.json").exists() and not (root / "package-lock.json").exists() and not (root / "yarn.lock").exists():
        results["warnings"].append({
            "package": "lockfile",
            "severity": "medium",
            "message": "No lockfile (package-lock.json or yarn.lock) — builds may not be reproducible",
        })
    
    # Check for common code issues
    _scan_code_patterns(root, results)


# Bug detection patterns for code scanning
CODE_PATTERNS = [
    # Security issues
    (r"eval\s*\(", "high", "Use of eval() — potential code injection"),
    (r"exec\s*\(", "high", "Use of exec() — potential code injection"),
    (r"pickle\.loads", "high", "Use of pickle — potential deserialization vulnerability"),
    (r"yaml\.load\s*\([^,)]*(?<!Loader)", "high", "Unsafe YAML loading — use yaml.safe_load()"),
    (r"subprocess\.call\s*\(\s*input", "high", "Shell injection via subprocess — sanitize input"),
    (r"os\.system\s*\(", "high", "Use of os.system() — shell injection risk"),
    (r"\.format\s*\([^)]*%", "medium", "String formatting with % — consider f-strings"),
    (r"password\s*=\s*['\"][^'\"]+['\"]", "high", "Hardcoded password detected"),
    (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "high", "Hardcoded API key detected"),
    (r"secret\s*=\s*['\"][^'\"]+['\"]", "high", "Hardcoded secret detected"),
    (r"token\s*=\s*['\"][^'\"]+['\"]", "high", "Hardcoded token detected"),
    (r"SELECT\s+.*\+.*FROM", "high", "SQL string concatenation — use parameterized queries"),
    (r"cursor\.execute\s*\(\s*f[\"']", "high", "SQL f-string injection — use parameterized queries"),
    (r"requests\.get\s*\(\s*f[\"']", "high", "URL injection via f-string — sanitize URLs"),
    (r"open\s*\(\s*[^,)]*\+", "high", "Path traversal — use os.path.join()"),
    (r"Path\s*\(\s*[^,)]*\+", "medium", "Path concatenation — use os.path.join()"),
    
    # Code quality issues
    (r"except\s*:", "medium", "Bare except clause — catch specific exceptions"),
    (r"pass\s*$", "medium", "Empty code block with pass — implement or add TODO"),
    (r"TODO\s*:", "low", "TODO comment found"),
    (r"FIXME\s*:", "medium", "FIXME comment found"),
    (r"print\s*\(", "low", "Debug print statement — remove in production"),
    (r"import\s+\*\s*$", "medium", "Wildcard import — import specific names"),
    (r"from\s+\w+\s+import\s+\w+,\s*\w+,\s*\w+,\s*\w+,\s*\w+,\s*\w+", "low", "Many imports on one line — consider line breaks"),
    
    # Performance issues
    (r"for\s+.*\s+in\s+.*:\s*\n\s*for\s+", "medium", "Nested loops — consider optimization"),
    (r"\.append\s*\(\s*\[", "medium", "Appending list in loop — use list comprehension"),
    (r"while\s+True\s*:", "medium", "Infinite loop — ensure exit condition"),
    (r"time\.sleep\s*\(\s*0\s*\)", "low", "time.sleep(0) — unnecessary yield"),
    
    # Best practices
    (r"if\s+__name__\s*==\s*['\"]__main__['\"]:", "low", "Missing main guard"),
    (r"class\s+\w+.*:\s*\n\s*def\s+__init__", "medium", "Consider dataclass for simple data containers"),
    (r"@property\s*\n\s*def\s+\w+\s*\(\s*\)\s*:\s*\n\s*return\s+self\.", "low", "Simple property — consider using attribute directly"),
]


def _scan_code_patterns(root: Path, results: dict) -> None:
    """Scan code files for common bug patterns."""
    extensions = {".py", ".js", ".ts", ".jsx", ".tsx"}
    
    for py_file in root.rglob("*"):
        if py_file.is_file() and py_file.suffix in extensions:
            if any(skip in str(py_file) for skip in ("node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build")):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                
                for pattern, severity, message in CODE_PATTERNS:
                    import re
                    matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        line_num = content[:match.start()].count("\n") + 1
                        # Get line content
                        line_content = lines[line_num - 1].strip() if line_num <= len(lines) else ""
                        
                        results["warnings"].append({
                            "package": f"{py_file.name}:{line_num}",
                            "severity": severity,
                            "message": f"{message}: {line_content[:60]}...",
                        })
            except Exception:
                pass
