# Changelog

All notable changes to CortexCode will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2025-03-13

### Added

- **CodeWiki** — AI-powered documentation site generator with `cortexcode wiki` command
  - Multi-page wiki with AI-generated content (Overview, Architecture, Code Flows, API Reference, Concepts Guide)
  - Per-module documentation pages for each Python/JS file
  - Mermaid diagram rendering support
  - Concept mapping and concept search ("how does authentication work?")
  - Token tracking per page
  - Supports Google Gemini, OpenAI, Anthropic, and Ollama providers
- **Interactive Visualization** — `cortexcode diagrams --viz` generates premium dark-mode HTML with glassmorphism, force-directed + hierarchical layouts, click-to-inspect nodes
- **MCP Setup Wizard** — `cortexcode mcp setup` auto-detects IDEs (VS Code, Cursor, Windsurf, Claude, Cline, RooCode, Gemini CLI, Amazon Q) and creates configs
- **Pre-indexed Bundles** — `cortexcode bundle export/import/info` for sharing indexes across team as `.ccb` files
- **Package Indexing** — `cortexcode package index <name>` indexes external packages (pip, npm)
- **Background Jobs** — `cortexcode jobs list/clear/watch` tracks indexing progress
- **Ask command** — `cortexcode ask "question"` - Ask natural language questions about your codebase
- **Flow Tracing** — `cortexcode analyze trace <symbol>` traces code flow through call graph; `cortexcode analyze flow <concept>` groups symbols by file
- **Git Hook Integration** — `cortexcode githook install/uninstall/precommit` for auto-indexing and security scanning
- **Shell Completion** — `cortexcode completion install/show/paths` for bash, zsh, fish, PowerShell
- **Short CLI Alias** — `cc` now works as a shortcut for `cortexcode`
- **Grouped Commands** — Commands organized into logical groups (`analyze`, `generate`, `serve`, `ai`) with legacy shortcuts still working
- **Project Website** — Astro + Tailwind CSS site with Vercel deployment (`website/`)
- **Cookbook** — `COOKBOOK.md` with practical recipes for all common workflows
- **VSCode extension wiki command** — Added `cortexcode.wiki` command and `/wiki`, `/ask` chat commands
- **Mermaid diagram rendering** — Fixed rendering in generated wiki with proper SVG output

### Changed

- **HTML Report Design** — Complete visual overhaul: glassmorphism cards, gradient accents, backdrop blur, JetBrains Mono + Outfit fonts, radial gradient backgrounds, premium dark theme matching viz quality
- **Graph Label Rendering** — Labels truncated to 16 characters with background rects and increased collision radius to prevent overlaps in both viz and HTML report graphs

- **Default provider** — Changed from OpenAI to Google/Gemini as the default AI provider
- **Code organization** — Reorganized flat files into subpackages:
  - `cortexcode/cli/` — CLI command handlers
  - `cortexcode/mcp/` — MCP server modules
  - `cortexcode/analysis/` — Analysis modules
  - `cortexcode/performance/` — Performance modules
  - `cortexcode/context/` — Context provider modules
  - `cortexcode/advanced_analysis/` — Advanced analysis modules

### Fixed

- **Module page navigation** — Fixed backslash escaping in JavaScript for module page links
- **Wiki list styles** — Improved CSS for ordered/unordered lists with custom bullets
- **Mermaid errors** — Fixed "Unable to render this Mermaid diagram" error by using correct v11 API

## [0.3.0] - 2025-03-01

### Added

- **Flutter/Dart support** — Regex-based symbol extraction for `.dart` files with full Flutter framework detection (StatelessWidget, StatefulWidget, Bloc, Riverpod, GetX, Provider, Firebase)
- **Kotlin support** — Tree-sitter AST extraction for `.kt`/`.kts` files with Android framework detection (Activity, Fragment, ViewModel, Compose, Room, Hilt, Ktor)
- **Swift support** — Tree-sitter AST extraction for `.swift` files with iOS framework detection (SwiftUI, UIKit, Combine, Core Data, Vapor)
- **React Native detection** — Identifies React Native components, hooks (`useNavigation`, `useRoute`), and utilities (`StyleSheet.create`, `Dimensions`)
- **Expo detection** — Detects Expo SDK usage and expo-router patterns
- **Android detection** — Activities, Fragments, ViewModels, Services, BroadcastReceivers, Room DAOs, Hilt DI in both Java and Kotlin
- **iOS detection** — SwiftUI Views, UIKit ViewControllers, Combine publishers, Core Data entities
- **Django/Flask detection** — Django views, DRF APIViews, Flask routes
- **Remix detection** — Loader and action functions
- **Multi-repo workspace** — `cortexcode workspace init/add/remove/list/index/search` commands to manage and query across multiple repositories
- **Plugin system** — Custom framework extractors via `.cortexcode/plugins.json` config. Plugins can register file extensions, symbol extractors, framework detectors, and post-processors
- **Dead code detection** — `cortexcode dead-code` finds symbols that are defined but never called or imported by any other symbol, with smart filtering for entry points, lifecycle methods, and framework-wired symbols
- **Complexity metrics** — `cortexcode complexity` analyzes all functions with cyclomatic complexity, nesting depth, line count, parameter count, and a 0-100 composite score with low/medium/high/critical ratings
- **Change impact analysis** — `cortexcode impact <symbol>` shows direct callers, indirect callers (2nd degree), affected files, affected tests, and importing files with risk assessment
- **Copilot Chat participant** — `@cortexcode` in VS Code Copilot Chat with `/search`, `/context`, `/impact`, `/deadcode`, `/complexity` commands
- **Live dashboard** — `cortexcode dashboard` serves HTML report with auto-refresh: polls for index changes and reloads the browser automatically when files are re-indexed
- **Offline HTML report** — D3.js is now bundled locally alongside the HTML; report works fully without internet
- **Web dashboard** — `cortexcode dashboard` launches a live HTTP server serving the interactive HTML report with auto-open in browser
- **Optional mobile deps** — `pip install cortexcode[mobile]` installs tree-sitter-kotlin and tree-sitter-swift

### Improved

- **Framework detection** — Greatly expanded: now detects 18+ frameworks across web, mobile, and backend (was 8)
- **Next.js App Router** — Detects `generateMetadata`, `generateStaticParams`, `'use server'`, `'use client'`
- **NestJS guards/pipes** — Detects `@Guard`, `CanActivate`, `@Pipe`, `PipeTransform`
- **Angular directives/pipes** — Detects `@Directive` and `@Pipe` decorators
- **HTML report** — Complete rewrite: donut charts (D3.js) for symbol types and languages, top files/callers bar charts, interactive call graph with zoom/filter/highlight/details panel, file dependency graph tab, improved search, responsive layout
- **Symbol cards** — Badge system with type/framework/doc badges, improved modal with calls/callers clickable links
- **Dart backslash paths** — Fixed file tree generation for Windows paths

## [0.2.0] - 2024-03-01

### Added

- **MCP server** — `cortexcode mcp` starts a Model Context Protocol server for direct AI agent integration with 7 tools (search, context, file_symbols, call_graph, diff, stats, file_deps)
- **LSP server** — `cortexcode lsp` starts a Language Server Protocol server providing hover, go-to-definition, and document symbols for any LSP-compatible editor
- **Semantic search** — `cortexcode find "auth handler"` uses TF-IDF with synonym expansion to find symbols by meaning, not just name
- **Git diff context** — `cortexcode diff` shows changed symbols since last commit, marks which are in changed line ranges, and identifies affected callers
- **Dependency scanning** — `cortexcode scan` checks package.json, requirements.txt, pyproject.toml, go.mod, Cargo.toml for security issues (unpinned versions, insecure protocols, missing lockfiles, exposed .env)
- **Cross-file type inference** — Index now includes `type_map` resolving imported symbols to their source definitions across files
- **File dependency graph** — Index now includes `file_dependencies` mapping which files import from which
- **Symbol search** — `cortexcode search "handle"` with `--type` and `--file` filters
- **Tiktoken support** — Token counting uses tiktoken when installed (`pip install cortexcode[ai]`), falls back to heuristic
- **CI/CD GitHub Action** — `.github/workflows/index.yml` template for auto-indexing on push
- **VS Code Marketplace prep** — Extension package.json updated with license, repository, keywords, categories

### Improved

- **Call graph (JS/TS)** — Fixed `call_expression` detection; went from ~0 to 90%+ symbols having call data
- **Arrow function detection** — `const X = () => {}` patterns now properly extracted
- **Member expression calls** — `obj.method()` calls captured via property_identifier fallback
- **Export handling** — `export default function` and `export const` properly unwrapped
- **Docstring/JSDoc extraction** — Python docstrings from AST body, JSDoc from preceding comments, truncated to 200 chars
- **Enum detection** — TypeScript enums now indexed
- **Return type extraction** — TypeScript return type annotations included
- **Fuzzy search** — Context command supports fuzzy matching (e.g. "hndlAuth" matches "handleAuth")
- **File-scoped queries** — `cortexcode context "auth.ts:"` returns all symbols in that file
- **Ranking** — Results ranked by call graph connectivity, symbol type, and match quality
- **Interface members** — TypeScript interface property names now extracted

## [0.1.0] - 2024-03-01

### Added

- **Multi-language AST indexing** — Python, JavaScript, TypeScript, Go, Rust, Java, C# via tree-sitter
- **Symbol extraction** — Functions, classes, methods with params, calls, type annotations
- **Call graph** — Track which functions call which
- **Import/export tracking** — Module dependencies
- **API route detection** — Express, FastAPI, NestJS, Spring Boot, ASP.NET
- **Entity/model detection** — Database models and ORM entities
- **Framework detection** — React, Angular, Next.js, NestJS, Express, Spring Boot, FastAPI, ASP.NET
- **Interactive HTML docs** — D3.js call graph, global search, file tree, symbol browser
- **Markdown docs** — Auto-generated README, API, STRUCTURE, FLOWS docs
- **Context provider** — `cortexcode context` for AI assistant integration
- **Token savings analysis** — `cortexcode stats` shows how many tokens CortexCode saves
- **Incremental indexing** — `cortexcode index -i` only re-indexes changed files
- **File watcher** — `cortexcode watch` auto-reindexes on file changes
- **VS Code extension** — Hover tooltips, go-to-definition, context panel, symbol list
- **`.gitignore` support** — Respects nested `.gitignore` files
- **Rich CLI** — Progress bars, panels, tables via Rich library
