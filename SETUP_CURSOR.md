# CortexCode Quick Start Guide for Cursor

A step-by-step guide to set up CortexCode with Cursor IDE.

---

## Step 1: Install CortexCode

Open your terminal and run:

```bash
pip install cortexcode
```

---

## Step 2: Index Your Project

Navigate to your project folder and run:

```bash
cd your-project-folder
cortexcode index
```

This creates `.cortexcode/index.json` with your project's code structure.

---

## Step 3: Configure Cursor Rules

Create a file `.cursor/rules.md` in your project root (same level as `.gitignore`):

```markdown
Always use CortexCode index (.cortexcode/index.json) to understand the codebase before making changes. Use:
- cortexcode search <symbol> to find symbols
- cortexcode impact <symbol> to see what uses a function
- cortexcode context <query> to get relevant code context

Run 'cortexcode index' first if the index doesn't exist.
```

---

## Step 4: Test It

Open your project in Cursor and ask:

> "Find where the function `your-function-name` is defined and show me all its callers"

Cursor will read the rules and use the CortexCode index to find the answer efficiently.

---

## Troubleshooting

**Q: Cursor doesn't see the rules?**
A: Make sure `.cursor/rules.md` is in the project root, not in a subfolder.

**Q: Index is outdated?**
A: Run `cortexcode index` again to refresh.

**Q: Want MCP integration?**
A: Add this to your Cursor settings (`~/.cursor/settings.json`):
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

---

## Learn More

- PyPI: https://pypi.org/project/cortexcode/
- VS Code Extension: https://marketplace.visualstudio.com/items?itemName=cortexcode.cortexcode-vscode
- GitHub: https://github.com/naveen-joshi/cortexcode
