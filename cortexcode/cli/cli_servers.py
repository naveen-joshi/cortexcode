import json
import os
import shutil
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt


IDE_CONFIGS = {
    "vscode": {
        "name": "VS Code",
        "file": ".vscode/settings.json",
        "config": {"mcpServers": {"cortexcode": {"command": "cortexcode", "args": ["mcp"], "disabled": False}}},
    },
    "cursor": {
        "name": "Cursor",
        "file": ".cursor/settings.json",
        "config": {"mcpServers": {"cortexcode": {"command": "cortexcode", "args": ["mcp"], "disabled": False}}},
    },
    "windsurf": {
        "name": "Windsurf",
        "file": ".windsurf/config.json",
        "config": {"mcpServers": {"cortexcode": {"command": "cortexcode", "args": ["mcp"], "disabled": False}}},
    },
    "claude": {
        "name": "Claude Desktop",
        "file": "claude_desktop_config.json",
        "config": {"mcpServers": {"cortexcode": {"command": "cortexcode", "args": ["mcp"], "disabled": False}}},
    },
    "cline": {
        "name": "Cline",
        "file": ".cline/settings.json",
        "config": {"mcpServers": {"cortexcode": {"command": "cortexcode", "args": ["mcp"], "disabled": False}}},
    },
    "roocode": {
        "name": "RooCode",
        "file": ".roocode/settings.json",
        "config": {"mcpServers": {"cortexcode": {"command": "cortexcode", "args": ["mcp"], "disabled": False}}},
    },
    "gemini": {
        "name": "Gemini CLI",
        "file": ".gemini/settings.json",
        "config": {"mcpServers": {"cortexcode": {"command": "cortexcode", "args": ["mcp"], "disabled": False}}},
    },
    "amazonq": {
        "name": "Amazon Q Developer",
        "file": ".aws/amazonq/settings.json",
        "config": {"mcpServers": {"cortexcode": {"command": "cortexcode", "args": ["mcp"], "disabled": False}}},
    },
}


def detect_ide() -> list[str]:
    """Detect which IDEs are available in the current environment."""
    detected = []
    home = Path.home()
    
    if (home / ".vscode/settings.json").exists():
        detected.append("vscode")
    if (home / ".cursor/settings.json").exists():
        detected.append("cursor")
    if (home / ".windsurf/config.json").exists():
        detected.append("windsurf")
    if (home / "AppData/Roaming/Claude/settings.json").exists() or (home / ".claude/settings.json").exists():
        detected.append("claude")
    if (home / ".cline/settings.json").exists():
        detected.append("cline")
    if (home / ".roocode/settings.json").exists():
        detected.append("roocode")
    if (home / ".gemini/settings.json").exists():
        detected.append("gemini")
    if (home / ".aws/amazonq/settings.json").exists():
        detected.append("amazonq")
    
    return detected


def handle_mcp_setup(console: Console) -> None:
    """Interactive MCP setup wizard."""
    console.print("\n[bold cyan]🔧 CortexCode MCP Setup Wizard[/bold cyan]\n")
    
    detected = detect_ide()
    
    console.print("[bold]Available IDEs:[/bold]")
    for key, ide in IDE_CONFIGS.items():
        status = "✓ detected" if key in detected else ""
        console.print(f"  • {ide['name']:25} {status}")
    
    console.print("\n[bold]Select IDE to configure:[/bold]")
    for i, (key, ide) in enumerate(IDE_CONFIGS.items(), 1):
        console.print(f"  {i}. {ide['name']}")
    console.print(f"  {len(IDE_CONFIGS) + 1}. All detected")
    console.print(f"  {len(IDE_CONFIGS) + 2}. Custom (enter path)")
    
    choice = Prompt.ask("\n[cyan]Choose[/cyan]", default="1")
    
    try:
        choice_num = int(choice)
        if choice_num == len(IDE_CONFIGS) + 1:
            targets = detected if detected else ["vscode"]
        elif choice_num == len(IDE_CONFIGS) + 2:
            custom_path = Prompt.ask("[cyan]Enter config file path[/cyan]")
            targets = [f"custom:{custom_path}"]
        elif 1 <= choice_num <= len(IDE_CONFIGS):
            targets = [list(IDE_CONFIGS.keys())[choice_num - 1]]
        else:
            console.print("[red]Invalid choice[/red]")
            return
    except ValueError:
        console.print("[red]Please enter a number[/red]")
        return
    
    for target in targets:
        if target.startswith("custom:"):
            config_path = Path(target.split(":", 1)[1])
        else:
            ide = IDE_CONFIGS.get(target)
            if not ide:
                continue
            config_path = Path.cwd() / ide["file"]
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        existing = {}
        if config_path.exists():
            try:
                existing = json.loads(config_path.read_text())
            except:
                pass
        
        mcp_key = "mcpServers"
        if mcp_key not in existing:
            existing[mcp_key] = {}
        
        existing[mcp_key]["cortexcode"] = {
            "command": "cortexcode",
            "args": ["mcp"],
            "disabled": False,
            "alwaysAllow": [],
        }
        
        config_path.write_text(json.dumps(existing, indent=2))
        console.print(f"[green]✓[/green] Updated {config_path}")
    
    console.print("\n[bold green]MCP setup complete![/bold green]")
    console.print("\n[dim]To start using CortexCode with your IDE:[/dim]")
    console.print("  1. Restart your IDE")
    console.print("  2. Run [cyan]cortexcode index[/cyan] in your project")
    console.print("  3. Start chatting with AI - it will have access to your code context!")


def handle_mcp_command(console: Console, run_stdio_server) -> None:
    console.print("[dim]CortexCode MCP server started (stdin/stdout)[/dim]")
    run_stdio_server()


def handle_lsp_command(run_lsp_server) -> None:
    run_lsp_server()
