from copy import deepcopy


TOOL_DEFINITIONS = [
    {
        "name": "cortexcode_search",
        "description": "USE THIS when user asks to find, locate, search for a function, class, method, or any code symbol. Also use when you need to know where something is defined. Returns type, file, line, params, and calls.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for - function name, class name, or any code symbol"},
                "type": {"type": "string", "description": "Filter by type: function, class, method, interface", "enum": ["function", "class", "method", "interface"]},
                "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "cortexcode_context",
        "description": "USE THIS when you need to understand how a function/class works, see its implementation, or see what it calls/who calls it. Also use when user asks 'how does X work' or 'show me the code for X'. Returns ACTUAL CODE SNIPPETS from the index - no need to read files separately. This saves tokens and time.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Symbol name to get context for, or 'file:symbol' for specific file"},
                "num_results": {"type": "integer", "description": "Number of results", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "cortexcode_file_symbols",
        "description": "USE THIS when you need to see all functions/classes in a specific file, or understand what a file exports/defines.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative file path (e.g. 'src/auth.ts')"},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "cortexcode_call_graph",
        "description": "USE THIS when you need to trace what functions call what, or find all callers of a function. Also use when user asks 'what uses this function' or 'where is this called'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol name to trace"},
                "depth": {"type": "integer", "description": "Depth of traversal (default 1)", "default": 1},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "cortexcode_diff",
        "description": "USE THIS when you need to find what code changed, or see modified functions. Also use when user asks 'what changed' or 'what was modified recently'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ref": {"type": "string", "description": "Git ref to compare against (default HEAD)", "default": "HEAD"},
            },
        },
    },
    {
        "name": "cortexcode_stats",
        "description": "USE THIS when user asks about project size, file count, language distribution, or wants to know 'how big is the project'.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "cortexcode_deadcode",
        "description": "USE THIS when user asks to find unused, unreachable, or dead code. Also use when user asks 'what functions are not used' or 'show me dead code'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
            },
        },
    },
    {
        "name": "cortexcode_complexity",
        "description": "USE THIS when user asks about code complexity, most complex functions, or which functions are hard to maintain. Also use when user asks 'what is the most complex code' or 'show me complex functions'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
            },
        },
    },
    {
        "name": "cortexcode_impact",
        "description": "USE THIS when user asks about change impact, what would break if they modify something, or which functions depend on a symbol. Also use when user asks 'what will break if I change X' or 'show me what uses this function'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol name to analyze impact for"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "cortexcode_file_deps",
        "description": "USE THIS when you need to find what files import from what, or trace file dependencies. Also use when user asks 'what does this file depend on'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "File to check dependencies for (optional, returns all if omitted)"},
            },
        },
    },
    {
        "name": "cortexcode_fuzzy_search",
        "description": "USE THIS when exact search returns no results, or user has a typo or partial name. Fuzzy search finds approximate matches using similarity scoring.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Approximate symbol name to search for"},
                "threshold": {"type": "number", "description": "Minimum similarity score 0-1 (default 0.5)", "default": 0.5},
                "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "cortexcode_regex_search",
        "description": "USE THIS when user wants to search with a pattern, like 'find all getters' or 'functions starting with handle'. Supports regex patterns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to match symbol names (e.g. '^get.*', 'handle.*Request$')"},
                "type": {"type": "string", "description": "Filter by type: function, class, method, interface", "enum": ["function", "class", "method", "interface"]},
                "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "cortexcode_duplicates",
        "description": "USE THIS when user asks about code duplication, copy-paste code, or repeated logic. Finds exact and near-duplicate functions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "min_lines": {"type": "integer", "description": "Minimum function lines to consider (default 5)", "default": 5},
            },
        },
    },
    {
        "name": "cortexcode_security_scan",
        "description": "USE THIS when user asks about security issues, vulnerabilities, hardcoded secrets, SQL injection, or XSS risks. Scans source code for common security problems.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "cortexcode_circular_deps",
        "description": "USE THIS when user asks about circular dependencies, import cycles, or dependency loops.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "cortexcode_endpoints",
        "description": "USE THIS when user asks about API endpoints, routes, REST APIs, or wants a list of all URLs/paths in the app. Detects Express, Flask, FastAPI, Django, Next.js, Spring, Go, Rails routes.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "cortexcode_api_docs",
        "description": "USE THIS when user asks to generate documentation, see doc coverage, or find undocumented functions. Auto-generates API docs from signatures and docstrings.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


TOOL_HANDLERS = {
    "cortexcode_search": "_tool_search",
    "cortexcode_context": "_tool_context",
    "cortexcode_file_symbols": "_tool_file_symbols",
    "cortexcode_call_graph": "_tool_call_graph",
    "cortexcode_diff": "_tool_diff",
    "cortexcode_stats": "_tool_stats",
    "cortexcode_deadcode": "_tool_deadcode",
    "cortexcode_complexity": "_tool_complexity",
    "cortexcode_impact": "_tool_impact",
    "cortexcode_file_deps": "_tool_file_deps",
    "cortexcode_fuzzy_search": "_tool_fuzzy_search",
    "cortexcode_regex_search": "_tool_regex_search",
    "cortexcode_duplicates": "_tool_duplicates",
    "cortexcode_security_scan": "_tool_security_scan",
    "cortexcode_circular_deps": "_tool_circular_deps",
    "cortexcode_endpoints": "_tool_endpoints",
    "cortexcode_api_docs": "_tool_api_docs",
}


def get_mcp_tools() -> list[dict]:
    """Return a defensive copy of the available MCP tool definitions."""
    return deepcopy(TOOL_DEFINITIONS)
