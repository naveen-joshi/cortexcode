# Contributing to CortexCode

Thanks for your interest in contributing! CortexCode is an open-source project and we welcome contributions.

## Getting Started

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/cortexcode.git
   cd cortexcode
   ```
3. **Install** in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

## Development

### Project Structure

```
cortexcode/
├── cortexcode/           # Python package
│   ├── cli.py            # CLI commands (click)
│   ├── indexer.py         # AST-based code indexer (tree-sitter)
│   ├── context.py         # Context provider for AI assistants
│   ├── docs.py            # Documentation generator
│   └── watcher.py         # File watcher for auto-reindex
├── cortexcode-vscode/     # VS Code extension
│   ├── src/extension.ts   # Extension source
│   └── package.json       # Extension manifest
├── tests/                 # Test suite
├── pyproject.toml         # Package config
└── README.md
```

### Running Tests

```bash
pytest
pytest --cov=cortexcode
```

### Linting

```bash
ruff check cortexcode/
ruff format cortexcode/
```

### Testing the CLI

```bash
# Index a test project
cortexcode index /path/to/project

# Check token savings
cortexcode stats

# Generate docs
cortexcode docs --open
```

### Testing the VS Code Extension

```bash
cd cortexcode-vscode
npm install
npm run compile
# Press F5 in VS Code to launch extension dev host
```

## How to Contribute

### Reporting Bugs

- Open an issue with a clear title and description
- Include steps to reproduce, expected vs actual behavior
- Include your Python version and OS

### Suggesting Features

- Open an issue with the `enhancement` label
- Describe the use case and why it would be useful

### Submitting Pull Requests

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Add tests for new functionality
4. Run `pytest` and `ruff check` to verify
5. Commit with a clear message: `git commit -m "Add: feature description"`
6. Push and open a PR

### Commit Message Format

```
Add: new feature description
Fix: bug description
Improve: enhancement description
Docs: documentation change
Refactor: code restructuring
```

## Areas for Contribution

- **Language support** — Add tree-sitter grammars for new languages
- **Framework detection** — Improve heuristics for detecting frameworks
- **Token estimation** — More accurate token counting (tiktoken integration)
- **VS Code extension** — Add features like CodeLens, tree view, diagnostics
- **Performance** — Optimize indexing for large codebases
- **Documentation** — Improve README, add tutorials, examples

## Code of Conduct

Be respectful and constructive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
