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

                if version in ("*", "latest", ""):
                    results["warnings"].append({
                        "package": name,
                        "severity": "medium",
                        "message": f"Unpinned version '{version}' — use a specific version range",
                    })

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
    if version.startswith("http://") or version.startswith("git://"):
        results["warnings"].append({
            "package": name,
            "severity": "high",
            "message": "Insecure protocol in dependency URL",
        })


def _check_common_issues(root: Path, results: dict) -> None:
    """Check for common security issues in the project."""
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

    if (root / "package.json").exists() and not (root / "package-lock.json").exists() and not (root / "yarn.lock").exists():
        results["warnings"].append({
            "package": "lockfile",
            "severity": "medium",
            "message": "No lockfile (package-lock.json or yarn.lock) — builds may not be reproducible",
        })

    _scan_code_patterns(root, results)


# ── Patterns ────────────────────────────────────────────────────────────────
# Each entry: (compiled_regex, severity, message_template)
# message_template may contain one {match} placeholder for the matched text.

_SECRET_VALUE = re.compile(
    r"""(['"])[a-zA-Z0-9+/=_\-!@#$%^&*]{8,}\1"""  # non-trivial quoted string (8+ chars)
)
_SAFE_RHS = re.compile(
    r"""(os\.(environ|getenv)\b|config\.(get|setting)\b|settings\.\w|getattr\(|environ\[|os\.env|None\b|['"]{2}|['"]{2})""",
    re.IGNORECASE,
)

# Code-quality patterns: (regex_source, severity, message, skip_comments)
# skip_comments=True means lines that are pure comments are ignored.
# Set to False for patterns that ARE expected to appear in comments (TODO/FIXME).
_CODE_PATTERNS: list[tuple[str, str, str, bool]] = [
    # Security — injection risks (skip_comments=True)
    (r"eval\s*\(", "high", "Use of eval() — potential code injection", True),
    (r"exec\s*\(", "high", "Use of exec() — potential code injection", True),
    (r"pickle\.loads\b", "high", "pickle.loads — potential deserialization vulnerability", True),
    (r"yaml\.load\s*\([^)]*\)", "high", "Unsafe yaml.load() — use yaml.safe_load()", True),
    (r"os\.system\s*\(", "high", "os.system() — shell injection risk, prefer subprocess", True),
    (r"subprocess\.(call|run|Popen)\s*\([^,)]*shell\s*=\s*True", "high", "subprocess with shell=True — injection risk", True),
    # SQL injection
    (r'cursor\.execute\s*\(\s*f["\']', "high", "SQL f-string injection — use parameterized queries", True),
    (r'execute\s*\(\s*["\'].*["\'].+%\s*\(', "high", "SQL %-formatting injection — use parameterized queries", True),
    (r'SELECT\s+\*?\s+FROM\s+\w+.*\+', "high", "SQL string concatenation — use parameterized queries", True),
    # Path traversal
    (r"open\s*\(\s*(?:request|user_input|data)\b", "high", "open() with user-controlled path — validate first", True),
    # XSS
    (r"mark_safe\s*\(", "medium", "Django mark_safe() — ensure content is sanitized", True),
    (r"Markup\s*\(", "medium", "Jinja2 Markup() — ensure content is sanitized", True),
    # Code quality
    (r"except\s*:", "medium", "Bare except: — catch specific exceptions instead", True),
    # TODO/FIXME live IN comments — do not skip comment lines for these
    (r"#\s*TODO\b", "low", "TODO comment — track in issue tracker", False),
    (r"#\s*FIXME\b", "medium", "FIXME comment — unresolved known issue", False),
    (r"from\s+\S+\s+import\s+\*", "medium", "Wildcard import — import specific names", True),
    (r"while\s+True\s*:", "low", "Infinite loop — verify exit condition is reachable", True),
    # Performance
    (r"time\.sleep\s*\(\s*0\s*\)", "low", "time.sleep(0) — unnecessary sleep", True),
]

_COMPILED_PATTERNS: list[tuple[re.Pattern, str, str, bool]] = [
    (re.compile(pat, re.IGNORECASE | re.MULTILINE), sev, msg, skip_comments)
    for pat, sev, msg, skip_comments in _CODE_PATTERNS
]

# Hardcoded-secret patterns — checked separately with false-positive filtering
_SECRET_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'(?:password|passwd|pwd)\s*=\s*', re.IGNORECASE), "Hardcoded password"),
    (re.compile(r'(?:api[_-]?key|apikey)\s*=\s*', re.IGNORECASE), "Hardcoded API key"),
    (re.compile(r'(?:secret[_-]?key|secret)\s*=\s*', re.IGNORECASE), "Hardcoded secret"),
    (re.compile(r'(?:access[_-]?token|auth[_-]?token|token)\s*=\s*', re.IGNORECASE), "Hardcoded token"),
    (re.compile(r'(?:private[_-]?key)\s*=\s*', re.IGNORECASE), "Hardcoded private key"),
]

_SKIP_DIRS = frozenset(("node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build", ".cortexcode"))
_SCAN_EXTENSIONS = frozenset((".py", ".js", ".ts", ".jsx", ".tsx"))


def _is_comment_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*")


def _is_safe_secret_rhs(rhs: str) -> bool:
    """Return True if the right-hand side of an assignment is not a literal secret."""
    rhs = rhs.strip()
    # Empty string, None, or variable reference
    if rhs in ('""', "''", "None", ""):
        return True
    # Reads from environment, config, or settings
    if _SAFE_RHS.search(rhs):
        return True
    # Plain identifier (e.g. SECRET_KEY = MY_SECRET_CONSTANT)
    if re.match(r'^[A-Z_][A-Z0-9_]*$', rhs):
        return True
    return False


def _scan_code_patterns(root: Path, results: dict) -> None:
    """Scan source files for known bug and security patterns.

    Warnings are grouped per file+pattern to avoid noise from repeated matches.
    """
    # Track seen (file, message) pairs to deduplicate
    seen: set[tuple[str, str]] = set()

    for src_file in root.rglob("*"):
        if not src_file.is_file():
            continue
        if src_file.suffix not in _SCAN_EXTENSIONS:
            continue
        if any(skip in src_file.parts for skip in _SKIP_DIRS):
            continue

        try:
            content = src_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        lines = content.splitlines()
        rel_name = str(src_file.relative_to(root))

        # ── General code patterns ────────────────────────────────────────
        for pattern, severity, message, skip_comments in _COMPILED_PATTERNS:
            first_line: int | None = None
            count = 0
            for m in pattern.finditer(content):
                line_num = content[: m.start()].count("\n") + 1
                if skip_comments and line_num <= len(lines) and _is_comment_line(lines[line_num - 1]):
                    continue
                if first_line is None:
                    first_line = line_num
                count += 1

            if first_line is None:
                continue

            key = (rel_name, message)
            if key in seen:
                continue
            seen.add(key)

            suffix = f" ({count} occurrences)" if count > 1 else f" (line {first_line})"
            results["warnings"].append({
                "package": rel_name,
                "severity": severity,
                "message": f"{message}{suffix}",
            })

        # ── Hardcoded-secret patterns (with false-positive filtering) ────
        for pattern, label in _SECRET_PATTERNS:
            first_line = None
            count = 0
            for m in pattern.finditer(content):
                line_num = content[: m.start()].count("\n") + 1
                raw_line = lines[line_num - 1] if line_num <= len(lines) else ""

                if _is_comment_line(raw_line):
                    continue

                # Extract the RHS of the assignment.
                # m.end() is absolute in `content`; compute the line-relative offset.
                line_start = content.rfind("\n", 0, m.start()) + 1
                rhs = raw_line[m.end() - line_start:].split("#")[0].strip()
                if _is_safe_secret_rhs(rhs):
                    continue
                # Require a non-trivial quoted string on the RHS
                if not _SECRET_VALUE.search(rhs):
                    continue

                if first_line is None:
                    first_line = line_num
                count += 1

            if first_line is None:
                continue

            key = (rel_name, label)
            if key in seen:
                continue
            seen.add(key)

            suffix = f" ({count} occurrences)" if count > 1 else f" (line {first_line})"
            results["warnings"].append({
                "package": rel_name,
                "severity": "high",
                "message": f"{label} detected{suffix}",
            })
