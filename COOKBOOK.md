# CortexCode Cookbook

Practical recipes for common workflows. All examples use the short `cc` alias — `cortexcode` works identically.

---

## Table of Contents

- [Getting Started](#getting-started)
- [AI-Powered Workflows](#ai-powered-workflows)
- [Code Analysis](#code-analysis)
- [Documentation Generation](#documentation-generation)
- [IDE & Agent Integration](#ide--agent-integration)
- [Team Collaboration](#team-collaboration)
- [CI/CD Integration](#cicd-integration)
- [Advanced Recipes](#advanced-recipes)

---

## Getting Started

### Recipe: First-Time Setup

```bash
# Install CortexCode
pip install cortexcode

# Navigate to your project
cd my-project

# Index the codebase
cc index

# See what you saved
cc analyze stats
```

### Recipe: Incremental Re-index After Changes

```bash
# Only re-index changed files (much faster)
cc index -i
```

### Recipe: Auto-Reindex on File Save

```bash
# Start the watcher — it re-indexes whenever you save a file
cc serve watch
```

### Recipe: Set Up Configuration

```bash
# Initialize a .cortexcode.yaml config file
cc config init

# Edit settings (exclude paths, set AI provider, etc.)
cc config show
```

---

## AI-Powered Workflows

### Recipe: Ask Questions About Your Code

```bash
# Ask a natural language question
cc ai ask "how does authentication work in this project?"

# Ask about a specific area
cc ai ask "what database models exist and how are they related?"

# Use a specific provider
cc ai ask "explain the API layer" --provider openai --model gpt-4o
```

### Recipe: Explain a Symbol

```bash
# Get an AI-generated explanation of a function or class
cc ai explain handleAuth

# With a specific provider
cc ai explain UserService --provider anthropic
```

### Recipe: Generate a CodeWiki

```bash
# Generate a full documentation site with AI
cc ai wiki --open

# Use Google Gemini (default) with specific pages
cc ai wiki --pages overview --pages architecture

# Skip per-module pages for a faster build
cc ai wiki --no-modules

# Limit module pages for large projects
cc ai wiki --max-modules 10
```

### Recipe: Generate AI Documentation

```bash
# Generate markdown docs powered by AI
cc ai docs

# Output to a custom directory
cc ai docs --output docs/ai-generated

# Choose which docs to generate
cc ai docs --docs overview --docs api --docs architecture
```

---

## Code Analysis

### Recipe: Trace a Code Flow

```bash
# Trace how a function is called and what it calls
cc analyze trace handleLogin

# Trace with depth limit
cc analyze trace handleLogin --depth 3
```

### Recipe: Understand a Concept

```bash
# Ask "how does X work?" without AI — uses keyword + graph analysis
cc analyze flow authentication

# Trace entry points for a concept
cc analyze flow "user registration"
```

### Recipe: Find Unused Code

```bash
# Detect symbols that are defined but never called
cc analyze dead-code

# Filter by type
cc analyze dead-code --type function
```

### Recipe: Complexity Analysis

```bash
# Show the most complex functions
cc analyze complexity

# Only show high-complexity (score > 50)
cc analyze complexity --min-score 50

# Top 5 most complex
cc analyze complexity --top 5
```

### Recipe: Change Impact Analysis

```bash
# Before refactoring: see what depends on a symbol
cc analyze impact createUser

# Check what files would be affected
cc analyze impact DatabaseConnection
```

### Recipe: Security Scan

```bash
# Scan dependencies for vulnerabilities
cc analyze scan

# Check for code-level security issues
cc analyze scan --code
```

### Recipe: Search Symbols

```bash
# Grep-like search
cc analyze search "handleAuth"

# Filter by type
cc analyze search "User" --type class

# Filter by file
cc analyze search "create" --file "auth.ts"

# Semantic search — find by meaning
cc analyze find "authentication handler"
cc analyze find "database models"
```

### Recipe: Git Diff Context

```bash
# See what symbols changed since last commit
cc analyze diff

# Compare against a specific ref
cc analyze diff --ref HEAD~5

# Compare against a branch
cc analyze diff --ref main
```

---

## Documentation Generation

### Recipe: Interactive HTML Docs

```bash
# Generate and open in browser
cc generate docs --open

# The output is at .cortexcode/docs/index.html
```

### Recipe: Mermaid Diagrams

```bash
# Generate Mermaid diagram files
cc generate diagrams

# Interactive D3.js visualization (premium dark mode)
cc generate diagrams --viz
```

### Recipe: Terminal Reports

```bash
# Show project overview in terminal
cc generate report

# Specific report type
cc generate report --type tech
cc generate report --type hotspots
cc generate report --type routes
```

---

## IDE & Agent Integration

### Recipe: One-Command MCP Setup

```bash
# Auto-detect installed IDEs and configure MCP
cc mcp setup

# This writes config for VS Code, Cursor, Windsurf, Claude Desktop, etc.
```

### Recipe: Manual MCP Configuration

Add to your IDE's MCP config (e.g., `~/.cursor/mcp.json`):

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

### Recipe: Use with Windsurf Rules

Add to `.windsurf/rules.md`:

```markdown
Always use CortexCode index (.cortexcode/index.json) to understand the codebase.
- Use `cc analyze search <symbol>` to find symbols
- Use `cc analyze impact <symbol>` to see what uses a function
- Use `cc analyze context <query>` to get relevant code context
Run `cc index` first if the index doesn't exist.
```

### Recipe: Shell Completion

```bash
# Install tab completion for your shell
cc completion install

# Show the completion script without installing
cc completion show

# Install for a specific shell
cc completion install --shell zsh
cc completion install --shell powershell
```

---

## Team Collaboration

### Recipe: Share Index as a Bundle

```bash
# Export your index as a .ccb bundle
cc bundle export

# Export with a custom name
cc bundle export --name my-project-v2

# Import a teammate's bundle
cc bundle import ./my-project.ccb

# Check bundle info before importing
cc bundle info ./my-project.ccb
```

### Recipe: Multi-Repo Workspace

```bash
# Initialize a workspace
cc workspace init

# Add repositories
cc workspace add ../backend
cc workspace add ../frontend
cc workspace add ../shared-lib

# Index all repos at once
cc workspace index

# Search across all repos
cc workspace search "handleAuth"
```

---

## CI/CD Integration

### Recipe: GitHub Action for Auto-Indexing

Create `.github/workflows/cortexcode.yml`:

```yaml
name: CortexCode Index
on:
  push:
    branches: [main]

jobs:
  index:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install cortexcode
      - run: cortexcode index
      - run: cortexcode analyze stats
```

### Recipe: Git Hook for Auto-Index

```bash
# Install a post-commit hook that re-indexes automatically
cc githook install

# Install a pre-commit hook for security scanning
cc githook precommit

# Remove hooks
cc githook uninstall
```

---

## Advanced Recipes

### Recipe: Index External Packages

```bash
# Index a pip package to understand its API
cc package index requests

# Index an npm package
cc package index express
```

### Recipe: Get AI-Ready Context (for Custom Scripts)

```bash
# Get structured context for a query (pipe to AI)
cc analyze context "handleAuth" --tokens

# Use in a script
CONTEXT=$(cc analyze context "database layer" 2>/dev/null)
echo "$CONTEXT" | your-ai-tool
```

### Recipe: Background Job Tracking

```bash
# List running/completed indexing jobs
cc jobs list

# Watch job progress in real-time
cc jobs watch

# Clear completed jobs
cc jobs clear
```

### Recipe: Live Dashboard

```bash
# Launch a web dashboard that auto-refreshes
cc serve dashboard

# It opens at http://localhost:8765
# Changes to the index are reflected automatically
```

### Recipe: Full Project Onboarding

A complete workflow for understanding a new codebase:

```bash
# 1. Index the project
cc index

# 2. Get an overview
cc analyze stats
cc generate report --type overview

# 3. Understand the architecture
cc generate diagrams --viz
cc ai ask "what is the high-level architecture?"

# 4. Generate full documentation
cc ai wiki --open

# 5. Set up for ongoing use
cc mcp setup
cc githook install
cc completion install
```
