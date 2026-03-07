"""Concept index — map high-level concepts to code entities."""

from __future__ import annotations

import re
from typing import Any

from cortexcode.knowledge.models import ConceptEntry, Snippet
from cortexcode.knowledge.snippets import extract_symbol_snippet

# Concept keyword patterns: concept_name -> (keywords in symbol names/files, keyword aliases for NL queries)
CONCEPT_PATTERNS: dict[str, tuple[list[str], list[str]]] = {
    "authentication": (
        ["auth", "login", "logout", "signin", "signout", "sign_in", "sign_out",
         "authenticate", "credential", "token", "jwt", "oauth", "session",
         "password", "passwd", "verify_token", "refresh_token"],
        ["how does login work", "how does authentication work", "sign in",
         "user login", "how do users authenticate", "session management"],
    ),
    "authorization": (
        ["permission", "role", "rbac", "acl", "authorize", "guard", "policy",
         "can_access", "is_admin", "has_permission", "access_control"],
        ["who can access what", "permissions", "roles", "access control"],
    ),
    "database": (
        ["model", "schema", "migration", "query", "repository", "orm",
         "entity", "table", "column", "database", "db", "mongo", "postgres",
         "mysql", "sqlite", "prisma", "sequelize", "typeorm", "sqlalchemy",
         "django_model"],
        ["where is data stored", "database", "data model", "how is data structured"],
    ),
    "api": (
        ["route", "endpoint", "controller", "handler", "middleware",
         "request", "response", "rest", "graphql", "grpc", "api"],
        ["api endpoints", "routes", "how does the api work", "rest api"],
    ),
    "payment": (
        ["payment", "billing", "invoice", "subscription", "charge", "stripe",
         "paypal", "checkout", "cart", "order", "price", "refund"],
        ["how do payments work", "billing", "checkout flow", "payment processing"],
    ),
    "user_management": (
        ["user", "profile", "account", "register", "registration", "signup",
         "sign_up", "onboarding", "settings", "preferences"],
        ["user management", "user accounts", "registration", "how do users sign up"],
    ),
    "email": (
        ["email", "mail", "smtp", "notification", "send_email", "mailer",
         "template_email", "newsletter"],
        ["email sending", "notifications", "how are emails sent"],
    ),
    "file_handling": (
        ["upload", "download", "file", "storage", "s3", "blob", "attachment",
         "media", "image", "asset"],
        ["file uploads", "file storage", "how are files handled"],
    ),
    "testing": (
        ["test", "spec", "mock", "fixture", "assert", "expect", "jest",
         "pytest", "unittest", "cypress", "playwright"],
        ["testing", "how are tests organized", "test suite"],
    ),
    "configuration": (
        ["config", "setting", "env", "environment", "dotenv", "option",
         "constant", "default"],
        ["configuration", "settings", "environment variables", "how is the app configured"],
    ),
    "error_handling": (
        ["error", "exception", "catch", "throw", "raise", "fault", "retry",
         "fallback", "handler_error", "error_handler"],
        ["error handling", "how are errors handled", "exception handling"],
    ),
    "logging": (
        ["log", "logger", "logging", "debug", "trace", "audit", "monitor"],
        ["logging", "how is logging done", "monitoring"],
    ),
    "caching": (
        ["cache", "redis", "memcache", "memoize", "invalidate", "ttl"],
        ["caching", "how does caching work", "cache invalidation"],
    ),
    "scheduling": (
        ["cron", "schedule", "job", "queue", "worker", "task", "celery",
         "background", "async_task"],
        ["background jobs", "scheduling", "task queue", "how are tasks scheduled"],
    ),
    "search": (
        ["search", "index", "elasticsearch", "algolia", "fulltext", "query_search",
         "filter", "facet"],
        ["search functionality", "how does search work"],
    ),
}

_KEYWORD_RE_CACHE: dict[str, re.Pattern] = {}


def _keyword_pattern(keyword: str) -> re.Pattern:
    """Compile a case-insensitive pattern for a keyword."""
    if keyword not in _KEYWORD_RE_CACHE:
        escaped = re.escape(keyword)
        _KEYWORD_RE_CACHE[keyword] = re.compile(escaped, re.IGNORECASE)
    return _KEYWORD_RE_CACHE[keyword]


def _score_symbol(symbol: dict[str, Any], keywords: list[str]) -> int:
    """Score how strongly a symbol matches a concept's keywords."""
    name = symbol.get("name", "").lower()
    doc = symbol.get("doc", "").lower() if symbol.get("doc") else ""
    score = 0
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in name:
            score += 3
        if kw_lower in doc:
            score += 1
    return score


def _score_file(file_path: str, keywords: list[str]) -> int:
    """Score how strongly a file path matches a concept's keywords."""
    path_lower = file_path.lower()
    score = 0
    for kw in keywords:
        if kw.lower() in path_lower:
            score += 2
    return score


def build_concept_index(
    index_data: dict[str, Any],
    project_root: str,
    max_symbols_per_concept: int = 15,
    max_files_per_concept: int = 10,
    max_snippets_per_concept: int = 5,
) -> list[ConceptEntry]:
    """Build a concept index from the codebase index data."""
    files = index_data.get("files", {})
    call_graph = index_data.get("call_graph", {})
    concepts: list[ConceptEntry] = []

    for concept_name, (keywords, aliases) in CONCEPT_PATTERNS.items():
        # Score symbols
        scored_symbols: list[tuple[int, str, str, dict]] = []  # (score, file, name, sym)
        scored_files: list[tuple[int, str]] = []

        for file_path, file_data in files.items():
            file_score = _score_file(file_path, keywords)
            if file_score > 0:
                scored_files.append((file_score, file_path))

            symbols = file_data.get("symbols", []) if isinstance(file_data, dict) else file_data
            for sym in symbols:
                sym_score = _score_symbol(sym, keywords)
                if sym_score > 0:
                    scored_symbols.append((sym_score, file_path, sym.get("name", ""), sym))
                    # Also count toward file relevance
                    if file_score == 0:
                        scored_files.append((sym_score, file_path))

        if not scored_symbols and not scored_files:
            continue

        # Deduplicate and sort
        scored_symbols.sort(key=lambda x: -x[0])
        seen_files: dict[str, int] = {}
        for score, fp in scored_files:
            if fp not in seen_files or score > seen_files[fp]:
                seen_files[fp] = score
        top_files = sorted(seen_files.items(), key=lambda x: -x[1])[:max_files_per_concept]

        top_syms = scored_symbols[:max_symbols_per_concept]
        related_symbols = [s[2] for s in top_syms]
        related_files = [f[0] for f in top_files]

        # Build call flows for top symbols
        related_flows: list[list[str]] = []
        for _, _, sym_name, _ in top_syms[:5]:
            callees = call_graph.get(sym_name, [])
            if callees:
                related_flows.append([sym_name] + callees[:5])

        # Extract snippets for top symbols
        snippets: list[Snippet] = []
        for _, fp, _, sym in top_syms[:max_snippets_per_concept]:
            snip = extract_symbol_snippet(project_root, fp, sym, context_lines=1, max_lines=20)
            if snip:
                snippets.append(snip)

        entry = ConceptEntry(
            name=concept_name,
            aliases=aliases,
            description="",  # Will be filled by AI generation later
            related_symbols=related_symbols,
            related_files=related_files,
            related_flows=related_flows,
            snippets=snippets,
        )
        concepts.append(entry)

    return concepts


def find_concept_for_query(
    concepts: list[ConceptEntry],
    query: str,
) -> list[ConceptEntry]:
    """Find concepts matching a natural language query, ranked by relevance."""
    query_lower = query.lower().strip()
    scored: list[tuple[float, ConceptEntry]] = []

    for concept in concepts:
        score = 0.0

        # Direct name match
        if concept.name.replace("_", " ") in query_lower:
            score += 10.0

        # Alias match
        for alias in concept.aliases:
            alias_lower = alias.lower()
            if alias_lower in query_lower or query_lower in alias_lower:
                score += 8.0
                break

        # Keyword overlap with query words
        query_words = set(re.split(r"\W+", query_lower))
        concept_words = set(re.split(r"\W+", concept.name.lower()))
        overlap = query_words & concept_words
        if overlap:
            score += len(overlap) * 3.0

        # Check related symbol names
        for sym in concept.related_symbols[:10]:
            sym_lower = sym.lower()
            for qw in query_words:
                if len(qw) > 2 and qw in sym_lower:
                    score += 1.0

        if score > 0:
            scored.append((score, concept))

    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored]
