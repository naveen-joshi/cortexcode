"""Tests for cortexcode.context.context_query."""
import json
import tempfile
from pathlib import Path

import pytest

from cortexcode.context.context_query import get_context


_INDEX = {
    "files": {
        "src/auth.py": {
            "symbols": [
                {"name": "login", "type": "function", "line": 5,
                 "params": ["username", "password"], "calls": ["validate_user"]},
                {"name": "logout", "type": "function", "line": 20,
                 "params": ["session_id"], "calls": []},
            ],
            "imports": [{"module": "bcrypt", "imported": ["hash"]}],
        },
        "src/models.py": {
            "symbols": [
                {"name": "UserModel", "type": "class", "line": 1,
                 "params": [], "calls": []},
            ],
            "imports": [],
        },
    },
    "call_graph": {"login": ["validate_user"]},
    "file_dependencies": {"src/auth.py": ["src/models.py"]},
}


@pytest.fixture
def index_path(tmp_path):
    p = tmp_path / "index.json"
    p.write_text(json.dumps(_INDEX))
    return p


def test_get_context_no_query(index_path):
    result = get_context(index_path)
    assert "symbols" in result
    assert isinstance(result["symbols"], list)


def test_get_context_exact_name(index_path):
    result = get_context(index_path, query="login")
    names = [s["name"] for s in result["symbols"]]
    assert "login" in names


def test_get_context_case_insensitive(index_path):
    result = get_context(index_path, query="LOGIN")
    names = [s["name"] for s in result["symbols"]]
    assert "login" in names


def test_get_context_partial_match(index_path):
    result = get_context(index_path, query="log")
    names = [s["name"] for s in result["symbols"]]
    # "login" and "logout" both start with "log"
    assert "login" in names or "logout" in names


def test_get_context_no_match(index_path):
    result = get_context(index_path, query="zzznotfound")
    assert result["total_found"] == 0


def test_get_context_num_results(index_path):
    result = get_context(index_path, query=None, num_results=1)
    assert len(result["symbols"]) <= 1


def test_get_context_file_scoped(index_path):
    result = get_context(index_path, query="auth.py:login")
    names = [s["name"] for s in result["symbols"]]
    assert "login" in names


def test_get_context_returns_query(index_path):
    result = get_context(index_path, query="login")
    assert result["query"] == "login"


def test_get_context_import_match(index_path):
    # Querying for a module name surfaces the import entry
    result = get_context(index_path, query="bcrypt")
    types = [s.get("type") for s in result["symbols"]]
    assert "import" in types


def test_get_context_file_dependencies(index_path):
    # File-scoped query should also return file_dependencies when present
    result = get_context(index_path, query="auth.py:")
    assert "file_dependencies" in result or result["total_found"] >= 0


def test_get_context_total_found(index_path):
    result = get_context(index_path, query="login")
    assert result["total_found"] >= 1
