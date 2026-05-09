"""Tests for cortexcode.vuln_scan."""
import json
import tempfile
from pathlib import Path

import pytest

from cortexcode.vuln_scan import scan_dependencies


# ── Helper ────────────────────────────────────────────────────────────────────

def make_project(files: dict[str, str]) -> Path:
    """Write files into a temp dir and return the root."""
    tmp = tempfile.mkdtemp()
    root = Path(tmp)
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    return root


# ── Dependency scanning ───────────────────────────────────────────────────────

def test_scan_empty_project():
    root = make_project({})
    result = scan_dependencies(root)
    assert result["total_dependencies"] == 0
    assert result["total_warnings"] == 0


def test_scan_package_json_pinned():
    root = make_project({"package.json": json.dumps({
        "dependencies": {"express": "^4.18.0", "lodash": "4.17.21"},
        "devDependencies": {"jest": "29.0.0"},
    })})
    result = scan_dependencies(root)
    assert result["total_dependencies"] == 3
    # Pinned versions → no warnings for those
    pkg_names = {d["name"] for d in result["dependencies"]}
    assert "express" in pkg_names
    assert "jest" in pkg_names


def test_scan_package_json_unpinned_warns():
    root = make_project({"package.json": json.dumps({
        "dependencies": {"react": "latest", "vue": "*"},
    })})
    result = scan_dependencies(root)
    severities = {w["severity"] for w in result["warnings"]}
    assert "medium" in severities


def test_scan_package_json_insecure_url():
    root = make_project({"package.json": json.dumps({
        "dependencies": {"mylib": "http://example.com/mylib.tgz"},
    })})
    result = scan_dependencies(root)
    high_msgs = [w["message"] for w in result["warnings"] if w["severity"] == "high"]
    assert any("Insecure protocol" in m for m in high_msgs)


def test_scan_requirements_txt_pinned():
    root = make_project({"requirements.txt": "requests==2.31.0\nflask>=2.0"})
    result = scan_dependencies(root)
    assert result["total_dependencies"] == 2
    names = {d["name"] for d in result["dependencies"]}
    assert "requests" in names
    assert "flask" in names


def test_scan_requirements_txt_unpinned_warns():
    root = make_project({"requirements.txt": "requests\nflask"})
    result = scan_dependencies(root)
    assert result["total_warnings"] >= 2  # one per unpinned dep


def test_scan_pyproject_toml():
    root = make_project({"pyproject.toml": '[project]\ndependencies = [\n    "click>=8.0",\n    "rich>=13.0",\n]\n'})
    result = scan_dependencies(root)
    assert result["total_dependencies"] >= 1
    assert "pyproject.toml" in result["scanned_files"]


def test_scan_go_mod():
    root = make_project({"go.mod": "module example.com/myapp\ngo 1.21\nrequire (\n    github.com/gin-gonic/gin v1.9.0\n)"})
    result = scan_dependencies(root)
    names = {d["name"] for d in result["dependencies"]}
    assert "github.com/gin-gonic/gin" in names


def test_scan_cargo_toml():
    root = make_project({"Cargo.toml": "[package]\nname = \"myapp\"\n\n[dependencies]\nserde = \"1.0\"\ntokio = \"1.28\"\n"})
    result = scan_dependencies(root)
    names = {d["name"] for d in result["dependencies"]}
    assert "serde" in names
    assert "tokio" in names


# ── .env warning ──────────────────────────────────────────────────────────────

def test_env_not_gitignored_warns():
    root = make_project({".env": "SECRET=abc123"})
    result = scan_dependencies(root)
    high_msgs = [w["message"] for w in result["warnings"] if w["severity"] == "high"]
    assert any(".env" in m for m in high_msgs)


def test_env_gitignored_no_warn():
    root = make_project({".env": "SECRET=abc123", ".gitignore": ".env\n"})
    result = scan_dependencies(root)
    env_warns = [w for w in result["warnings"] if ".env" in w.get("message", "")]
    assert env_warns == []


# ── Code pattern scanning ─────────────────────────────────────────────────────

def test_eval_detected():
    root = make_project({"app.py": "result = eval(user_input)\n"})
    result = scan_dependencies(root)
    msgs = [w["message"] for w in result["warnings"]]
    assert any("eval" in m.lower() for m in msgs)


def test_hardcoded_password_detected():
    root = make_project({"config.py": 'password = "super_secret_123"\n'})
    result = scan_dependencies(root)
    msgs = [w["message"] for w in result["warnings"]]
    assert any("password" in m.lower() or "hardcoded" in m.lower() for m in msgs)


def test_env_var_password_not_flagged():
    root = make_project({"config.py": 'password = os.getenv("DB_PASS")\n'})
    result = scan_dependencies(root)
    high_msgs = [w["message"] for w in result["warnings"] if w["severity"] == "high"
                 and "password" in w["message"].lower()]
    assert high_msgs == []


def test_empty_string_password_not_flagged():
    root = make_project({"config.py": 'password = ""\n'})
    result = scan_dependencies(root)
    high_msgs = [w["message"] for w in result["warnings"] if w["severity"] == "high"
                 and "password" in w["message"].lower()]
    assert high_msgs == []


def test_comment_line_not_flagged():
    root = make_project({"app.py": "# password = 'hardcoded'\n"})
    result = scan_dependencies(root)
    high_msgs = [w["message"] for w in result["warnings"] if w["severity"] == "high"
                 and "password" in w["message"].lower()]
    assert high_msgs == []


def test_sql_injection_detected():
    root = make_project({"db.py": 'cursor.execute(f"SELECT * FROM users WHERE id={user_id}")\n'})
    result = scan_dependencies(root)
    msgs = [w["message"] for w in result["warnings"]]
    assert any("sql" in m.lower() or "injection" in m.lower() for m in msgs)


def test_os_system_detected():
    root = make_project({"run.py": 'os.system("rm -rf " + user_dir)\n'})
    result = scan_dependencies(root)
    msgs = [w["message"] for w in result["warnings"]]
    assert any("os.system" in m for m in msgs)


def test_yaml_load_detected():
    root = make_project({"load.py": "data = yaml.load(stream)\n"})
    result = scan_dependencies(root)
    msgs = [w["message"] for w in result["warnings"]]
    assert any("yaml" in m.lower() for m in msgs)


def test_deduplication_same_pattern():
    # Ten eval() calls in the same file → only ONE warning entry for that pattern
    code = "eval(x)\n" * 10
    root = make_project({"app.py": code})
    result = scan_dependencies(root)
    eval_warns = [w for w in result["warnings"] if "eval" in w["message"].lower()]
    assert len(eval_warns) == 1


def test_todo_low_severity():
    root = make_project({"app.py": "# TODO: fix this later\n"})
    result = scan_dependencies(root)
    low_msgs = [w for w in result["warnings"] if w["severity"] == "low"
                and "TODO" in w["message"]]
    assert low_msgs  # at least one low-severity TODO warning


def test_bare_except_medium_severity():
    root = make_project({"app.py": "try:\n    pass\nexcept:\n    pass\n"})
    result = scan_dependencies(root)
    medium_msgs = [w for w in result["warnings"] if w["severity"] == "medium"
                   and "except" in w["message"].lower()]
    assert medium_msgs


def test_no_lockfile_warns():
    root = make_project({"package.json": json.dumps({"dependencies": {"express": "4.0.0"}})})
    result = scan_dependencies(root)
    lockfile_warns = [w for w in result["warnings"] if "lockfile" in w["message"].lower()]
    assert lockfile_warns


def test_skips_node_modules():
    root = make_project({
        "node_modules/some-lib/index.js": "eval(dangerous)\n",
        "app.py": "print('hello')\n",
    })
    result = scan_dependencies(root)
    node_mod_warns = [w for w in result["warnings"]
                      if "node_modules" in str(w.get("package", ""))]
    assert node_mod_warns == []
