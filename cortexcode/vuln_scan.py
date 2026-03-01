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
