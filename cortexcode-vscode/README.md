# CortexCode - AI Code Index

Lightweight code indexing for AI assistants. Use `@cortexcode` in Copilot Chat or configure MCP to enable AI agents to understand your codebase.

## Features

- **Copilot Chat Integration** — Use `@cortexcode` in Copilot Chat to query your codebase
- **MCP Server** — AI agents can use CortexCode tools via Model Context Protocol
- **Hover Tooltips** — Hover over any symbol to see its definition
- **Go to Definition** — Ctrl+Click on any symbol to jump to its definition
- **Auto-indexing** — Automatically indexes your project on open
- **Live Updates** — Re-indexes when files change

## Installation

### From VS Code Marketplace
Search for "CortexCode" in VS Code extensions and install.

### From Open VSX (Windsurf, VSCodium)
Search for "CortexCode" in your editor's extension marketplace.

## Copilot Chat Commands

In Copilot Chat, use these commands with `@cortexcode`:

| Command | Description |
|---------|-------------|
| `@cortexcode search <name>` | Search symbols by name |
| `@cortexcode /context <query>` | Get relevant code context |
| `@cortexcode /impact <symbol>` | Analyze change impact |
| `@cortexcode /deadcode` | Find unused symbols |
| `@cortexcode /complexity` | View complex functions |

## MCP Configuration (Windsurf, Cursor, Claude Desktop)

Add to your MCP config:

```json
{
  "mcpServers": {
    "cortexcode": {
      "command": "cortexcode",
      "args": ["mcp"]
    }
  }
}
```

### Available MCP Tools

| Tool | Description | Trigger Phrases |
|------|-------------|-----------------|
| `cortexcode_search` | Find symbols by name | "find", "search for", "where is" |
| `cortexcode_context` | Get symbol implementation | "how does X work", "show me code" |
| `cortexcode_file_symbols` | List symbols in a file | "symbols in file" |
| `cortexcode_call_graph` | Trace callers/callees | "what uses this", "where is called" |
| `cortexcode_diff` | Changed symbols | "what changed", "modified" |
| `cortexcode_stats` | Project statistics | "project size", "how big" |
| `cortexcode_deadcode` | Find unused code | "dead code", "not used" |
| `cortexcode_complexity` | Complex functions | "complex code", "hard to maintain" |
| `cortexcode_impact` | Change impact analysis | "what breaks", "impact of changing" |
| `cortexcode_file_deps` | File dependencies | "depends on", "imports" |

## Requirements

- VS Code 1.93+ / Windsurf / Cursor
- Python 3.10+
- CortexCode CLI (`pip install cortexcode`)

## Extension Settings

- `cortexcode.indexOnOpen` — Automatically index project when opened (default: true)
- `cortexcode.autoWatch` — Auto-reindex on file changes (default: true)

## For AI Agents

This extension exposes code intelligence capabilities. AI coding agents can:
- Find symbols by name across the entire codebase
- Get relevant context with call graph connectivity
- Analyze what would break if a symbol is changed
- Find potentially dead code
- Identify complex functions that need attention
- Trace file dependencies and imports

## License

MIT
