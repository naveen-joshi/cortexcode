"""Semantic search over symbols — find symbols by meaning, not just name.

Uses BM25 (Okapi BM25) instead of TF-IDF because code symbols are short
documents where length-normalization matters more than term frequency alone.
"""

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


# ── Tokenisation ─────────────────────────────────────────────────────────────

def tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens, splitting camelCase and snake_case."""
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', text)
    text = text.replace("_", " ").replace("-", " ").replace("/", " ").replace("\\", " ").replace(".", " ")
    return [t.lower() for t in re.findall(r'[a-zA-Z]{2,}', text)]


def _bigrams(tokens: list[str]) -> list[str]:
    """Return adjacent token pairs as 'a_b' strings."""
    return [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]


# ── Synonym expansion ─────────────────────────────────────────────────────────

_SYNONYMS: dict[str, list[str]] = {
    "auth": ["authentication", "authorize", "login", "signin", "credentials", "session", "token", "jwt"],
    "authentication": ["auth", "login", "signin", "credentials"],
    "login": ["auth", "signin", "authentication", "credentials"],
    "logout": ["signout", "revoke", "invalidate"],
    "handler": ["handle", "controller", "action", "endpoint", "route", "api"],
    "controller": ["handler", "endpoint", "route"],
    "middleware": ["interceptor", "filter", "guard", "hook"],
    "database": ["db", "model", "entity", "schema", "orm", "query", "repository", "store", "dao"],
    "model": ["entity", "schema", "database", "db", "struct"],
    "user": ["account", "profile", "member", "customer", "person"],
    "create": ["add", "new", "insert", "post", "register", "save", "init"],
    "delete": ["remove", "destroy", "drop", "clear"],
    "update": ["edit", "modify", "patch", "put", "save", "set"],
    "get": ["fetch", "read", "find", "query", "retrieve", "list", "load", "select"],
    "list": ["get", "fetch", "all", "index", "browse", "paginate"],
    "component": ["widget", "ui", "view", "page", "screen", "element"],
    "page": ["screen", "view", "route", "component"],
    "api": ["endpoint", "route", "handler", "rest", "graphql", "rpc"],
    "route": ["endpoint", "api", "path", "handler", "url"],
    "test": ["spec", "assert", "expect", "mock", "fixture", "suite"],
    "error": ["exception", "catch", "throw", "fail", "panic", "fault"],
    "config": ["configuration", "settings", "options", "env", "params", "props"],
    "nav": ["navigation", "menu", "sidebar", "header", "breadcrumb"],
    "button": ["btn", "click", "action", "trigger"],
    "submit": ["send", "post", "save", "confirm", "dispatch"],
    "validate": ["check", "verify", "assert", "sanitize", "guard"],
    "search": ["find", "query", "filter", "lookup", "seek"],
    "file": ["upload", "download", "document", "attachment", "asset"],
    "notification": ["alert", "message", "toast", "notify", "event"],
    "schedule": ["calendar", "booking", "appointment", "cron", "timer"],
    "cache": ["store", "memoize", "persist", "buffer", "redis"],
    "log": ["logger", "trace", "debug", "monitor", "record"],
    "parse": ["decode", "deserialize", "read", "extract", "transform"],
    "format": ["encode", "serialize", "render", "print", "stringify"],
    "queue": ["job", "task", "worker", "consumer", "producer"],
    "permission": ["role", "acl", "access", "policy", "grant"],
    "payment": ["billing", "invoice", "charge", "subscription", "stripe"],
    "email": ["mail", "smtp", "sendgrid", "message", "notification"],
    "image": ["photo", "picture", "thumbnail", "media", "upload"],
}


def expand_query(query_tokens: list[str]) -> list[str]:
    """Expand query tokens with synonyms for better recall."""
    expanded = list(query_tokens)
    for token in query_tokens:
        for syn in _SYNONYMS.get(token, []):
            if syn not in expanded:
                expanded.append(syn)
    return expanded


# ── Document building ─────────────────────────────────────────────────────────

def build_symbol_documents(index: dict) -> list[dict]:
    """Build searchable documents from index symbols."""
    docs = []
    files = index.get("files", {})
    call_graph = index.get("call_graph", {})

    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue

        file_tokens = tokenize(rel_path.replace("/", " ").replace("\\", " "))

        for sym in file_data.get("symbols", []):
            name = sym.get("name", "")
            # Core symbol tokens: name, params, calls, doc, class, framework type
            parts = [name]
            parts.extend(sym.get("params", []))
            parts.extend(sym.get("calls", []))
            if sym.get("doc"):
                parts.append(sym["doc"])
            if sym.get("class"):
                parts.append(sym["class"])
            if sym.get("framework"):
                parts.append(sym["framework"])
            if sym.get("type"):
                parts.append(sym["type"])

            text = " ".join(str(p) for p in parts)
            base_tokens = tokenize(text)
            # BM25 document = symbol content only (not file path).
            # File path is stored separately for a small context bonus.
            tokens = base_tokens + _bigrams(base_tokens)

            # Connectivity score from call graph
            callers = sum(
                1 for callees in call_graph.values() if name in callees
            )

            docs.append({
                "name": name,
                "type": sym.get("type"),
                "file": rel_path,
                "line": sym.get("line"),
                "params": sym.get("params", []),
                "calls": sym.get("calls", []),
                "doc": sym.get("doc"),
                "framework": sym.get("framework"),
                "tokens": tokens,
                "name_tokens": tokenize(name),
                "file_tokens": file_tokens,
                "callers": callers,
            })

    return docs


# ── BM25 ─────────────────────────────────────────────────────────────────────

class BM25Searcher:
    """Okapi BM25 ranker over symbol documents.

    BM25 handles short documents better than TF-IDF because it saturates
    term-frequency (via k1) and applies length normalization (via b), so a
    symbol name appearing twice in a two-token doc does not dominate over a
    symbol with a richer but longer description.
    """

    def __init__(self, documents: list[dict], k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        self._idf: dict[str, float] = {}
        self._avgdl: float = 0.0
        self._build()

    def _build(self) -> None:
        n = len(self.documents)
        if n == 0:
            return

        total_len = sum(len(d["tokens"]) for d in self.documents)
        self._avgdl = total_len / n

        doc_freq: Counter = Counter()
        for doc in self.documents:
            for term in set(doc["tokens"]):
                doc_freq[term] += 1

        for term, df in doc_freq.items():
            self._idf[term] = math.log((n - df + 0.5) / (df + 0.5) + 1)

    def _score(self, query_terms: list[str], doc: dict) -> float:
        tf_map = Counter(doc["tokens"])
        dl = len(doc["tokens"]) or 1
        k1, b, avgdl = self.k1, self.b, self._avgdl

        score = 0.0
        for term in query_terms:
            idf = self._idf.get(term, 0.0)
            tf = tf_map.get(term, 0)
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * dl / avgdl)
            score += idf * numerator / denominator if denominator else 0.0
        return score

    def search(self, query: str, limit: int = 10) -> list[dict]:
        base_tokens = tokenize(query)
        if not base_tokens:
            return []

        expanded = expand_query(base_tokens)
        query_terms = expanded + _bigrams(expanded)

        scored: list[tuple[float, dict]] = []
        for doc in self.documents:
            score = self._score(query_terms, doc)

            # Exact name match bonus
            if any(qt in doc["name_tokens"] for qt in base_tokens):
                score += 3.0
            elif any(qt in doc["name_tokens"] for qt in expanded):
                score += 1.0

            # Prefix / morphological match bonus
            # Handles "auth"→"authenticate", "authentication"→"authenticate", etc.
            # Check both base tokens (strong) and expanded synonyms (weaker).
            for strength, token_set in ((1.2, base_tokens), (0.5, expanded)):
                for qt in token_set:
                    if qt in base_tokens and strength < 1.0:
                        continue  # already handled in the strong pass
                    for nt in doc["name_tokens"]:
                        if qt == nt:
                            continue
                        if nt.startswith(qt) or qt.startswith(nt):
                            score += strength
                            break
                        # Long common prefix (morphological variants like authenticate/authentication)
                        prefix_len = 0
                        for a, b in zip(qt, nt):
                            if a == b:
                                prefix_len += 1
                            else:
                                break
                        if prefix_len >= min(len(qt), len(nt)) * 0.75 and prefix_len >= 4:
                            score += strength
                            break

            # Docstring mention bonus
            if doc.get("doc"):
                doc_lower = doc["doc"].lower()
                if any(qt in doc_lower for qt in base_tokens):
                    score += 0.5

            # File-context bonus (smaller than name match — file name is shared context)
            if any(qt in doc["file_tokens"] for qt in expanded):
                score += 0.3

            # Caller-connectivity bonus — well-connected symbols are more likely to be relevant
            if doc["callers"] > 0:
                score += min(math.log1p(doc["callers"]) * 0.2, 1.0)

            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "name": doc["name"],
                "type": doc["type"],
                "file": doc["file"],
                "line": doc["line"],
                "params": doc["params"],
                "calls": doc["calls"][:5] if doc["calls"] else [],
                "doc": doc.get("doc"),
                "framework": doc.get("framework"),
                "score": round(score, 3),
            }
            for score, doc in scored[:limit]
        ]


# ── Public API ────────────────────────────────────────────────────────────────

def semantic_search(index_path: Path, query: str, limit: int = 10) -> dict[str, Any]:
    """Run BM25 semantic search over the index.

    Args:
        index_path: Path to index.json
        query: Natural language query (e.g. "authentication handler")
        limit: Max results

    Returns:
        Dictionary with ranked results and metadata.
    """
    index = json.loads(index_path.read_text(encoding="utf-8"))
    documents = build_symbol_documents(index)
    searcher = BM25Searcher(documents)
    results = searcher.search(query, limit)

    return {
        "query": query,
        "results": results,
        "total_symbols": len(documents),
    }
