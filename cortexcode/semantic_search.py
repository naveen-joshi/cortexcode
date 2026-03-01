"""Semantic search over symbols — find symbols by meaning, not just name."""

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


def tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens, splitting camelCase and snake_case."""
    # Split camelCase
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    # Split snake_case and kebab-case
    text = text.replace("_", " ").replace("-", " ").replace("/", " ").replace("\\", " ").replace(".", " ")
    # Lowercase and split
    tokens = [t.lower() for t in re.findall(r'[a-zA-Z]{2,}', text)]
    return tokens


# Common programming synonyms for semantic expansion
_SYNONYMS = {
    "auth": ["authentication", "authorize", "login", "signin", "credentials", "session", "token", "jwt"],
    "authentication": ["auth", "login", "signin", "credentials"],
    "login": ["auth", "signin", "authentication", "credentials"],
    "handler": ["handle", "controller", "action", "endpoint", "route", "api"],
    "controller": ["handler", "endpoint", "route"],
    "database": ["db", "model", "entity", "schema", "orm", "query", "repository", "store"],
    "model": ["entity", "schema", "database", "db"],
    "user": ["account", "profile", "member", "customer"],
    "create": ["add", "new", "insert", "post", "register", "save"],
    "delete": ["remove", "destroy", "drop"],
    "update": ["edit", "modify", "patch", "put", "save"],
    "get": ["fetch", "read", "find", "query", "retrieve", "list", "load"],
    "list": ["get", "fetch", "all", "index", "browse"],
    "component": ["widget", "ui", "view", "page", "screen"],
    "page": ["screen", "view", "route", "component"],
    "api": ["endpoint", "route", "handler", "rest"],
    "route": ["endpoint", "api", "path", "handler"],
    "test": ["spec", "assert", "expect", "mock"],
    "error": ["exception", "catch", "throw", "fail"],
    "config": ["configuration", "settings", "options", "env"],
    "nav": ["navigation", "menu", "sidebar", "header"],
    "button": ["btn", "click", "action"],
    "submit": ["send", "post", "save", "confirm"],
    "validate": ["check", "verify", "assert", "sanitize"],
    "search": ["find", "query", "filter", "lookup"],
    "file": ["upload", "download", "document", "attachment"],
    "notification": ["alert", "message", "toast", "notify"],
    "schedule": ["calendar", "booking", "appointment", "time"],
    "interview": ["meeting", "call", "session", "conversation"],
    "candidate": ["applicant", "user", "profile"],
    "job": ["position", "role", "posting", "vacancy"],
}


def expand_query(query_tokens: list[str]) -> list[str]:
    """Expand query tokens with synonyms for better recall."""
    expanded = list(query_tokens)
    for token in query_tokens:
        synonyms = _SYNONYMS.get(token, [])
        for syn in synonyms:
            if syn not in expanded:
                expanded.append(syn)
    return expanded


def build_symbol_documents(index: dict) -> list[dict]:
    """Build searchable documents from index symbols."""
    docs = []
    files = index.get("files", {})
    call_graph = index.get("call_graph", {})
    
    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue
        
        for sym in file_data.get("symbols", []):
            name = sym.get("name", "")
            # Build a rich text representation for search
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
            
            # Add file path context
            parts.append(rel_path.replace("/", " ").replace("\\", " "))
            
            text = " ".join(parts)
            tokens = tokenize(text)
            
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
                "text": text,
            })
    
    return docs


class TFIDFSearcher:
    """Simple TF-IDF based semantic search (no external dependencies)."""
    
    def __init__(self, documents: list[dict]):
        self.documents = documents
        self.idf: dict[str, float] = {}
        self._build_idf()
    
    def _build_idf(self):
        """Compute inverse document frequency for all terms."""
        n = len(self.documents)
        if n == 0:
            return
        
        doc_freq: dict[str, int] = Counter()
        for doc in self.documents:
            unique_tokens = set(doc["tokens"])
            for token in unique_tokens:
                doc_freq[token] += 1
        
        for token, df in doc_freq.items():
            self.idf[token] = math.log(n / (1 + df))
    
    def _tfidf_vector(self, tokens: list[str]) -> dict[str, float]:
        """Compute TF-IDF vector for a token list."""
        tf = Counter(tokens)
        total = len(tokens) or 1
        vector = {}
        for token, count in tf.items():
            tf_val = count / total
            idf_val = self.idf.get(token, 0)
            vector[token] = tf_val * idf_val
        return vector
    
    def _cosine_similarity(self, vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
        """Compute cosine similarity between two sparse vectors."""
        common = set(vec_a.keys()) & set(vec_b.keys())
        if not common:
            return 0.0
        
        dot = sum(vec_a[k] * vec_b[k] for k in common)
        mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
        mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
        
        if mag_a == 0 or mag_b == 0:
            return 0.0
        
        return dot / (mag_a * mag_b)
    
    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search documents by semantic similarity to query."""
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        
        # Expand with synonyms
        expanded_tokens = expand_query(query_tokens)
        query_vec = self._tfidf_vector(expanded_tokens)
        
        scored = []
        for doc in self.documents:
            doc_vec = self._tfidf_vector(doc["tokens"])
            score = self._cosine_similarity(query_vec, doc_vec)
            
            # Boost exact name matches
            name_tokens = tokenize(doc.get("name", ""))
            if any(qt in name_tokens for qt in query_tokens):
                score += 0.5
            # Boost partial name matches from expanded tokens
            elif any(qt in name_tokens for qt in expanded_tokens):
                score += 0.2
            
            # Boost doc/framework matches
            if doc.get("doc"):
                doc_lower = doc["doc"].lower()
                if any(qt in doc_lower for qt in query_tokens):
                    score += 0.15
            
            if score > 0.01:
                scored.append((score, doc))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, doc in scored[:limit]:
            results.append({
                "name": doc["name"],
                "type": doc["type"],
                "file": doc["file"],
                "line": doc["line"],
                "params": doc["params"],
                "calls": doc["calls"][:5] if doc["calls"] else [],
                "doc": doc.get("doc"),
                "framework": doc.get("framework"),
                "score": round(score, 3),
            })
        
        return results


def semantic_search(index_path: Path, query: str, limit: int = 10) -> dict[str, Any]:
    """Run semantic search over the index.
    
    Args:
        index_path: Path to index.json
        query: Natural language query (e.g. "authentication handler", "database models")
        limit: Max results
    
    Returns:
        Dictionary with ranked results
    """
    index = json.loads(index_path.read_text(encoding="utf-8"))
    documents = build_symbol_documents(index)
    
    searcher = TFIDFSearcher(documents)
    results = searcher.search(query, limit)
    
    return {
        "query": query,
        "results": results,
        "total_symbols": len(documents),
    }
