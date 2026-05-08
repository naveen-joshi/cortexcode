"""Tests for cortexcode.semantic_search (BM25-based)."""
import json
import tempfile
from pathlib import Path

import pytest

from cortexcode.semantic_search import (
    BM25Searcher,
    build_symbol_documents,
    expand_query,
    semantic_search,
    tokenize,
)


# ── tokenize ──────────────────────────────────────────────────────────────────

def test_tokenize_snake_case():
    assert tokenize("get_user_by_id") == ["get", "user", "by", "id"]


def test_tokenize_camel_case():
    assert tokenize("handleAuthRequest") == ["handle", "auth", "request"]


def test_tokenize_upper_camel():
    assert tokenize("UserAuthService") == ["user", "auth", "service"]


def test_tokenize_consecutive_caps():
    assert tokenize("parseHTTPResponse") == ["parse", "http", "response"]


def test_tokenize_short_words_stripped():
    tokens = tokenize("a_b_c_hello")
    assert "hello" in tokens
    # single-character tokens dropped (regex requires 2+ chars)
    assert "a" not in tokens


def test_tokenize_empty():
    assert tokenize("") == []


# ── expand_query ──────────────────────────────────────────────────────────────

def test_expand_auth():
    expanded = expand_query(["auth"])
    assert "authentication" in expanded
    assert "login" in expanded
    assert "jwt" in expanded


def test_expand_unknown_term():
    expanded = expand_query(["xyzzy"])
    assert expanded == ["xyzzy"]


def test_expand_no_duplicates():
    expanded = expand_query(["auth", "authentication"])
    # "auth" → adds "authentication", but "authentication" is already there
    assert expanded.count("authentication") == 1


def test_expand_multiple_tokens():
    expanded = expand_query(["auth", "handler"])
    assert "login" in expanded
    assert "controller" in expanded


# ── build_symbol_documents ────────────────────────────────────────────────────

_SIMPLE_INDEX = {
    "files": {
        "src/auth.py": {
            "symbols": [
                {"name": "authenticate", "type": "function", "line": 1,
                 "params": ["token"], "calls": ["verify_token"], "doc": "Verifies a JWT token."},
                {"name": "hash_password", "type": "function", "line": 20,
                 "params": ["password"], "calls": [], "doc": None},
            ],
            "imports": [],
        },
        "src/models.py": {
            "symbols": [
                {"name": "UserModel", "type": "class", "line": 1,
                 "params": [], "calls": [], "doc": "Database user entity."},
            ],
            "imports": [],
        },
    },
    "call_graph": {"authenticate": ["verify_token"]},
}


def test_build_symbol_documents_count():
    docs = build_symbol_documents(_SIMPLE_INDEX)
    assert len(docs) == 3


def test_build_symbol_documents_fields():
    docs = build_symbol_documents(_SIMPLE_INDEX)
    names = {d["name"] for d in docs}
    assert names == {"authenticate", "hash_password", "UserModel"}


def test_build_symbol_documents_name_tokens():
    docs = {d["name"]: d for d in build_symbol_documents(_SIMPLE_INDEX)}
    assert "authenticate" in docs["authenticate"]["name_tokens"]
    assert "hash" in docs["hash_password"]["name_tokens"]
    assert "password" in docs["hash_password"]["name_tokens"]


def test_build_symbol_documents_file_tokens_separate():
    docs = {d["name"]: d for d in build_symbol_documents(_SIMPLE_INDEX)}
    # file_tokens come from the path, NOT mixed into bm25 tokens
    assert "auth" in docs["authenticate"]["file_tokens"]
    # The bm25 tokens should NOT contain "auth" from the file path
    # (only from the function name / calls / params)
    bm25_tokens = docs["hash_password"]["tokens"]
    # hash_password has no auth-related content — should not have "auth" from path
    assert "auth" not in bm25_tokens


# ── BM25Searcher ──────────────────────────────────────────────────────────────

@pytest.fixture
def searcher():
    docs = build_symbol_documents(_SIMPLE_INDEX)
    return BM25Searcher(docs)


def test_bm25_exact_name_match(searcher):
    results = searcher.search("authenticate")
    assert results[0]["name"] == "authenticate"


def test_bm25_morphological_variant(searcher):
    # "authentication" shares long common prefix with "authenticate"
    results = searcher.search("authentication")
    assert results[0]["name"] == "authenticate"


def test_bm25_synonym_expansion(searcher):
    # "login" is a synonym of "auth" which prefix-matches "authenticate"
    results = searcher.search("login")
    assert results[0]["name"] == "authenticate"


def test_bm25_database_model(searcher):
    results = searcher.search("database model")
    assert results[0]["name"] == "UserModel"


def test_bm25_returns_scores(searcher):
    results = searcher.search("authenticate")
    assert all("score" in r for r in results)
    assert all(r["score"] > 0 for r in results)


def test_bm25_limit(searcher):
    results = searcher.search("auth", limit=1)
    assert len(results) == 1


def test_bm25_empty_query(searcher):
    results = searcher.search("")
    assert results == []


def test_bm25_no_match(searcher):
    results = searcher.search("zzz_nonexistent_zzz")
    assert results == []


def test_bm25_result_fields(searcher):
    results = searcher.search("authenticate")
    r = results[0]
    assert "name" in r
    assert "type" in r
    assert "file" in r
    assert "line" in r
    assert "params" in r
    assert "calls" in r
    assert "score" in r


# ── semantic_search (integration) ────────────────────────────────────────────

def test_semantic_search_integration():
    with tempfile.TemporaryDirectory() as tmp:
        index_path = Path(tmp) / "index.json"
        index_path.write_text(json.dumps(_SIMPLE_INDEX))

        result = semantic_search(index_path, "authentication")
        assert "query" in result
        assert "results" in result
        assert "total_symbols" in result
        assert result["total_symbols"] == 3
        assert result["results"][0]["name"] == "authenticate"
