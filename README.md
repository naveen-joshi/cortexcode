<p align="center">
  <h1 align="center">CortexCode</h1>
  <p align="center">
    <strong>Lightweight code indexing for AI assistants</strong><br>
    Save 90%+ tokens by giving AI agents structured context instead of raw source files.
  </p>
</p>

<p align="center">
  <a href="https://pypi.org/project/cortexcode/"><img src="https://img.shields.io/pypi/v/cortexcode?style=flat-square&color=blue" alt="PyPI"></a>
  <a href="https://pypi.org/project/cortexcode/"><img src="https://img.shields.io/pypi/pyversions/cortexcode?style=flat-square" alt="Python"></a>
  <a href="https://github.com/naveen-joshi/cortexcode/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"></a>
  <a href="https://github.com/naveen-joshi/cortexcode"><img src="https://img.shields.io/github/stars/naveen-joshi/cortexcode?style=flat-square" alt="Stars"></a>
  <a href="https://marketplace.visualstudio.com/items?itemName=cortexcode.cortexcode-vscode"><img src="https://img.shields.io/visual-studio-marketplace/v/cortexcode.cortexcode-vscode?style=flat-square" alt="VS Code"></a>
</p>

---

## The Problem

AI coding assistants (Copilot, Cursor, Windsurf, etc.) need to understand your codebase. The current approach: **dump entire source files into the context window**. This is:

- **Expensive** — A 150-file project can cost 200K+ tokens per query
- **Slow** — More tokens = slower responses
- **Wasteful** — Most of those tokens are irrelevant to the question

## The Solution

CortexCode indexes your codebase using **AST parsing** (tree-sitter) and provides a structured, searchable index. Instead of feeding 200K tokens of raw code, you feed **~500 tokens of relevant context**.

```
┌─────────────────────────────────────────────────┐
│  Without CortexCode          With CortexCode    │
│                                                  │
│  200,000 tokens    →         500 tokens          │
│  $0.006/query      →         $0.00002/query      │
│  All files dumped  →         Only relevant syms  │
│  No structure      →         Call graph + types   │
└─────────────────────────────────────────────────┘
```

Run `cortexcode stats` on your project to see your actual savings.

## Quick Start

```bash
# Install from PyPI
pip install cortexcode

# Or install from source
git clone https://github.com/cortexcode/cortexcode.git
cd cortexcode && pip install -e .

# Index your project
cd your-project
cortexcode index

# See token savings
cortexcode stats

# Get context for AI
cortexcode context "handleAuth"

# Generate interactive docs
cortexcode docs --open
```

## Features

### Multi-Language AST Indexing

Parses source code into structured symbols using tree-sitter grammars.

| Language | Extensions | Frameworks Detected |
|----------|-----------|-------------------|
| Python | `.py` | FastAPI, Django |
| JavaScript | `.js`, `.jsx` | React, Express, Angular |
| TypeScript | `.ts`, `.tsx` | Next.js, NestJS, Angular |
| Go | `.go` | — |
| Rust | `.rs` | — |
| Java | `.java` | Spring Boot |
| C# | `.cs` | ASP.NET |

### What Gets Indexed

- **Symbols** — Functions, classes, methods with parameters and return types
- **Call Graph** — Which functions call which (and who calls them)
- **Imports/Exports** — Module dependencies
- **API Routes** — Express, FastAPI, NestJS, Spring Boot endpoints
- **Entities** — Database models and ORM definitions
- **Framework Detection** — React components, Angular services, etc.

### Token Savings

CortexCode dramatically reduces the tokens needed to give AI assistants useful context:

```bash
$ cortexcode stats

╭──────── Token Savings Analysis ────────╮
│ Source files         154 files          │
│ Raw project tokens   203,847            │
│ Full index tokens    45,291             │
│ Context query tokens 487                │
│                                         │
│ Tokens saved         203,360            │
│ Savings              99.8%              │
│ Compression ratio    418.6x             │
╰─────────────────────────────────────────╯
```

### Interactive HTML Documentation

Generate a full interactive documentation site with:

- **File tree** browser
- **Symbol list** with filtering
- **D3.js call graph** visualization (draggable nodes)
- **Global search** across all symbols
- **Import/Export** browser
- **API route** listing
- **Framework** detection summary

```bash
cortexcode docs --open
```

### Incremental Indexing

Only re-index files that changed since last run:

```bash
cortexcode index -i    # Skip unchanged files
```

### VS Code Extension

Install from: [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=cortexcode.cortexcode-vscode)

The bundled VS Code extension provides:

- **Hover tooltips** — Hover any symbol to see type, params, callers
- **Go to definition** — Ctrl+Click using indexed data
- **Context panel** — View symbol details in a side panel
- **Status bar** — Shows indexed symbol count

```bash
cd cortexcode-vscode
npm install && npm run compile
# Press F5 to launch in VS Code
```

## Commands

| Command | Description |
|---------|-------------|
| `cortexcode index [path]` | Index a directory |
| `cortexcode index -i` | Incremental index (changed files only) |
| `cortexcode context [query]` | Get relevant context for AI |
| `cortexcode context [query] --tokens` | Show token savings for query |
| `cortexcode search [query]` | Grep-like symbol search with type/file filters |
| `cortexcode find [query]` | Semantic search by meaning ("auth handler") |
| `cortexcode diff` | Show changed symbols since last commit |
| `cortexcode diff --ref HEAD~3` | Compare against any git ref |
| `cortexcode stats` | Show project stats and token savings |
| `cortexcode scan` | Scan dependencies for security warnings |
| `cortexcode docs --open` | Generate and open interactive docs |
| `cortexcode dead-code` | Detect potentially unused symbols |
| `cortexcode complexity` | Analyze code complexity (cyclomatic, nesting, line count) |
| `cortexcode complexity --min-score 50` | Show only high-complexity functions |
| `cortexcode impact <symbol>` | Change impact analysis — what breaks if you modify a symbol |
| `cortexcode dashboard` | Launch live dashboard with auto-refresh on index changes |
| `cortexcode workspace init` | Initialize a multi-repo workspace |
| `cortexcode workspace add <path>` | Add a repo to the workspace |
| `cortexcode workspace list` | List repos in workspace |
| `cortexcode workspace index` | Index all workspace repos |
| `cortexcode workspace search <q>` | Search symbols across all repos |
| `cortexcode watch` | Auto-reindex on file changes |
| `cortexcode mcp` | Start MCP server for AI agent integration |
| `cortexcode lsp` | Start Language Server Protocol server |

## How AI Agents Use This

### 1. Context Command (simplest)

```bash
# Paste this output into your AI chat
cortexcode context "useAuth" --tokens
```

### 2. JSON Index (programmatic)

```python
import json

index = json.load(open('.cortexcode/index.json'))

# Get all functions
for path, data in index['files'].items():
    for sym in data['symbols']:
        print(f"{sym['type']}: {sym['name']} in {path}:{sym['line']}")

# Trace call graph
for caller, callees in index['call_graph'].items():
    for callee in callees:
        print(f"{caller} -> {callee}")
```

### 3. MCP Server

AI agents can query the index directly via the Model Context Protocol:

```bash
# Start the MCP server (stdin/stdout)
cortexcode mcp
```

**Configuration Examples:**

```json
// Claude Desktop (claude_desktop_config.json)
{
  "mcpServers": {
    "cortexcode": {
      "command": "cortexcode",
      "args": ["mcp"]
    }
  }
}

// Cursor / Windsurf
{
  "mcpServers": {
    "cortexcode": {
      "command": "cortexcode",
      "args": ["mcp"]
    }
  }
}

// Open WebUI / AnythingLLM
{
  "mcpServers": {
    "cortexcode": {
      "command": "cortexcode",
      "args": ["mcp"]
    }
  }
}
```

Available MCP tools:
- **`cortexcode_search`** — Search symbols by name
- **`cortexcode_context`** — Get rich context with callers/callees
- **`cortexcode_file_symbols`** — List all symbols in a file
- **`cortexcode_call_graph`** — Trace call graph for a symbol
- **`cortexcode_diff`** — Get changed symbols since last commit
- **`cortexcode_stats`** — Get project statistics
- **`cortexcode_deadcode`** — Find potentially unused symbols
- **`cortexcode_complexity`** — Find most complex functions
- **`cortexcode_impact`** — Analyze change impact of a symbol
- **`cortexcode_file_deps`** — Get file dependency graph

### 4. LSP Server

Any LSP-compatible editor can use CortexCode for hover, go-to-definition, and document symbols:

```bash
cortexcode lsp
```

### 5. Git Diff Context

See only what changed — perfect for code review:

```bash
# What symbols changed since last commit?
cortexcode diff

# Compare against a branch
cortexcode diff --ref main
```

### 6. Copilot Chat (`@cortexcode`)

In VS Code with the CortexCode extension, use `@cortexcode` in Copilot Chat:

```
@cortexcode search handleAuth
@cortexcode /context authentication
@cortexcode /impact createUser
@cortexcode /deadcode
@cortexcode /complexity
```

Commands:
- **`/search`** — Find symbols by name
- **`/context`** — Get ranked context for a query (relevance + call graph connectivity)
- **`/impact`** — Change impact analysis (direct/indirect callers, affected files/tests)
- **`/deadcode`** — List potentially unused symbols
- **`/complexity`** — Show most complex functions by params + outgoing calls

### 7. Semantic Search

Find symbols by meaning, not just name:

```bash
cortexcode find "authentication handler"
cortexcode find "database models"
cortexcode find "user login flow"
```

### 8. Code Analysis

```bash
# Find unused symbols
cortexcode dead-code

# Show top 10 most complex functions
cortexcode complexity --top 10

# What breaks if I change createUser?
cortexcode impact createUser
```

## Index Format

The index is stored at `.cortexcode/index.json`:

```json
{
  "project_root": "/path/to/project",
  "last_indexed": "2024-03-01T12:00:00",
  "languages": ["javascript", "typescript", "python"],
  "files": {
    "src/auth.ts": {
      "symbols": [
        {
          "name": "AuthService",
          "type": "class",
          "line": 10,
          "params": [],
          "calls": ["validateToken", "hashPassword"]
        }
      ],
      "imports": [{ "module": "bcrypt", "imported": ["hash", "compare"] }],
      "exports": [{ "name": "AuthService", "type": "class" }],
      "api_routes": [{ "method": "POST", "path": "/auth/login" }]
    }
  },
  "call_graph": {
    "AuthService": ["validateToken", "hashPassword"],
    "validateToken": ["jwt.verify"]
  }
}
```

## Configuration

CortexCode respects `.gitignore` files (including nested ones) and has built-in ignore patterns for:

- `node_modules/`, `__pycache__/`, `.git/`
- Build directories (`dist/`, `build/`, `.next/`)
- IDE files (`.idea/`, `.vscode/`)
- Package manager files (`vendor/`, `.venv/`)

## Roadmap

- [x] MCP server for direct AI agent integration
- [x] Tiktoken-based accurate token counting
- [x] Semantic search over symbols (TF-IDF + synonym expansion)
- [x] Cross-file type inference
- [x] Git diff-aware context (show only changed symbols)
- [x] Language server protocol (LSP) support
- [x] Dependency vulnerability scanning
- [x] CI/CD integration (GitHub Action)
- [x] Multi-repo workspace support
- [x] Custom plugin system for framework-specific extractors
- [x] Web dashboard for index visualization
- [x] Flutter/Dart language support (regex-based)
- [x] React Native / Expo framework detection
- [x] Native Android (Kotlin/Java) framework detection
- [x] Native iOS (Swift/SwiftUI/UIKit) framework detection
- [x] Django / Flask framework detection
- [x] VS Code Marketplace publishing

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Development install
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check cortexcode/
```

## License

MIT — See [LICENSE](LICENSE)
