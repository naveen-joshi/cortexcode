import re
from pathlib import Path
from typing import Any


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
    (r'innerHTML\s*=\s*(?![\'\"]\s*$)', "Potential XSS — innerHTML assignment", "medium"),
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

    file_paths = []
    if files:
        for rel_path in files:
            file_paths.append(root / rel_path)
    else:
        exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".php"}
        for ext in exts:
            file_paths.extend(root.rglob(f"*{ext}"))

    all_patterns = (
        [(pattern, description, severity, "secret") for pattern, description, severity in SECRET_PATTERNS]
        + [(pattern, description, severity, "sql_injection") for pattern, description, severity in SQL_INJECTION_PATTERNS]
        + [(pattern, description, severity, "xss") for pattern, description, severity in XSS_PATTERNS]
        + [(pattern, description, severity, "unsafe_code") for pattern, description, severity in UNSAFE_PATTERNS]
    )
    compiled = [(re.compile(pattern, re.IGNORECASE), description, severity, category) for pattern, description, severity, category in all_patterns]

    for file_path in file_paths:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        scanned_files += 1
        rel = str(file_path.relative_to(root))

        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
                continue
            is_test = "test" in rel.lower() or "spec" in rel.lower()

            for regex, description, severity, category in compiled:
                if is_test and category in ("unsafe_code",):
                    continue
                if regex.search(line):
                    findings.append({
                        "file": rel,
                        "line": line_num,
                        "category": category,
                        "severity": severity,
                        "description": description,
                        "snippet": stripped[:120],
                    })

    seen = set()
    unique_findings = []
    for finding in findings:
        key = (finding["file"], finding["line"], finding["category"])
        if key not in seen:
            seen.add(key)
            unique_findings.append(finding)

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    unique_findings.sort(key=lambda x: severity_order.get(x["severity"], 99))

    summary = {}
    for finding in unique_findings:
        category = finding["category"]
        summary[category] = summary.get(category, 0) + 1

    return {
        "scanned_files": scanned_files,
        "total_findings": len(unique_findings),
        "summary": summary,
        "severity_counts": {
            severity: sum(1 for finding in unique_findings if finding["severity"] == severity)
            for severity in ("critical", "high", "medium", "low")
        },
        "findings": unique_findings,
    }
