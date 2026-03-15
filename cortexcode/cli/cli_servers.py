import json
import os
import shutil
import platform
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt


IDE_CONFIGS = {
    "vscode": {
        "name": "VS Code",
        "file": ".vscode/mcp.json",
        "global_file": "~/.vscode/mcp.json",
        "config": {"servers": {"cortexcode": {"command": "cortexcode", "args": ["mcp", "start"]}}},
    },
    "cursor": {
        "name": "Cursor",
        "file": ".cursor/mcp.json",
        "global_file": "~/.cursor/mcp.json",
        "config": {"servers": {"cortexcode": {"command": "cortexcode", "args": ["mcp", "start"]}}},
    },
    "windsurf": {
        "name": "Windsurf",
        "file": ".codeium/windsurf/mcp_config.json",
        "global_file": "~/.codeium/windsurf/mcp_config.json",
        "config": {"mcpServers": {"cortexcode": {"command": "cortexcode", "args": ["mcp", "start"]}}},
    },
    "claude": {
        "name": "Claude Code",
        "file": None,
        "global_file": None,
        "config": None,
        "cli_command": "claude mcp add cortexcode stdio -- cortexcode mcp start",
    },
    "cline": {
        "name": "Cline",
        "file": ".cline/mcp.json",
        "global_file": "~/.cline/mcp.json",
        "config": {"mcpServers": {"cortexcode": {"command": "cortexcode", "args": ["mcp", "start"]}}},
    },
    "roocode": {
        "name": "RooCode",
        "file": ".roocode/mcp.json",
        "global_file": "~/.roocode/mcp.json",
        "config": {"mcpServers": {"cortexcode": {"command": "cortexcode", "args": ["mcp", "start"]}}},
    },
    "opencode": {
        "name": "OpenCode",
        "file": "opencode.json",
        "global_file": "~/.opencode/opencode.json",
        "config": {"mcp": {"cortexcode": {"type": "local", "command": ["cortexcode", "mcp", "start"], "enabled": True}}},
    },
    "antigravity": {
        "name": "Antigravity",
        "file": ".antigravity/mcp.json",
        "global_file": "~/.antigravity/mcp.json",
        "config": {"mcpServers": {"cortexcode": {"command": "cortexcode", "args": ["mcp", "start"]}}},
    },
}


def get_claude_config_path() -> Path:
    """Get Claude Desktop config path based on OS."""
    home = Path.home()
    system = platform.system()
    
    if system == "Windows":
        return home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    elif system == "Darwin":  # macOS
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:  # Linux
        return home / ".config" / "Claude" / "claude_desktop_config.json"


def detect_ide() -> list[str]:
    """Detect which IDEs are available in the current environment."""
    detected = []
    home = Path.home()
    
    # VS Code / Cursor mcp.json
    if (home / ".vscode/mcp.json").exists() or (Path.cwd() / ".vscode/mcp.json").exists():
        detected.append("vscode")
    if (home / ".cursor/mcp.json").exists():
        detected.append("cursor")
    
    # Windsurf
    if (home / ".codeium/windsurf/mcp_config.json").exists():
        detected.append("windsurf")
    
    # Claude Desktop
    if get_claude_config_path().exists():
        detected.append("claude")
    
    # Cline
    if (home / ".cline/mcp.json").exists():
        detected.append("cline")
    
    # RooCode
    if (home / ".roocode/mcp.json").exists():
        detected.append("roocode")
    
    # OpenCode
    if (Path.cwd() / "opencode.json").exists() or (home / ".opencode/opencode.json").exists():
        detected.append("opencode")
    
    # Antigravity
    if (home / ".antigravity/mcp.json").exists():
        detected.append("antigravity")
    
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
        ide = IDE_CONFIGS.get(target)
        
        if target == "claude":
            console.print(f"\n[yellow]Claude Code:[/yellow] Run this command manually:")
            console.print(f"  [cyan]{ide.get('cli_command')}[/cyan]")
            console.print("[dim]Then restart Claude Code[/dim]")
            continue
        
        if target == "opencode":
            config_path = Path.cwd() / ide["file"]
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            existing = {}
            if config_path.exists():
                try:
                    existing = json.loads(config_path.read_text())
                except:
                    pass
            
            if "mcp" not in existing:
                existing["mcp"] = {}
            existing["mcp"]["cortexcode"] = ide["config"]["mcp"]["cortexcode"]
            
            config_path.write_text(json.dumps(existing, indent=2))
            console.print(f"[green]✓[/green] Updated {config_path}")
            continue
        
        if target.startswith("custom:"):
            config_path = Path(target.split(":", 1)[1])
        else:
            config_path = Path.cwd() / ide["file"]
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        existing = {}
        if config_path.exists():
            try:
                existing = json.loads(config_path.read_text())
            except:
                pass
        
        # VS Code/Cursor use "servers", others use "mcpServers"
        if target in ("vscode", "cursor"):
            mcp_key = "servers"
        else:
            mcp_key = "mcpServers"
        
        if mcp_key not in existing:
            existing[mcp_key] = {}
        
        existing[mcp_key]["cortexcode"] = {
            "command": "cortexcode",
            "args": ["mcp"],
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
