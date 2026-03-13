"""Package indexing - index external packages (pip, npm, etc.)."""

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn


LANGUAGE_LOCATIONS = {
    "python": {
        "site_packages": lambda: Path(sys.prefix) / "Lib" / "site-packages",
        "src_patterns": ["**/*.py"],
    },
    "javascript": {
        "site_packages": lambda: Path.cwd() / "node_modules",
        "src_patterns": ["**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx"],
    },
    "typescript": {
        "site_packages": lambda: Path.cwd() / "node_modules",
        "src_patterns": ["**/*.ts", "**/*.tsx"],
    },
}


def find_package_location(package_name: str, language: str) -> Path | None:
    """Find where a package is installed."""
    if language == "python":
        try:
            spec = importlib.util.find_spec(package_name)
            if spec and spec.submodule_search_locations:
                return Path(spec.submodule_search_locations[0]).parent
        except Exception:
            pass
        
        site_packages = Path(sys.prefix) / "Lib" / "site-packages"
        if (site_packages / package_name).exists():
            return site_packages / package_name
        if (site_packages / f"{package_name}-*").exists():
            for p in site_packages.glob(f"{package_name}-*"):
                return p
    
    elif language in ("javascript", "typescript"):
        node_modules = Path.cwd() / "node_modules" / package_name
        if node_modules.exists():
            return node_modules
    
    return None


def index_package(package_name: str, language: str, output_dir: Path) -> dict:
    """Index a package and return the index data."""
    package_path = find_package_location(package_name, language)
    
    if not package_path:
        raise FileNotFoundError(f"Package '{package_name}' not found. Install it first: pip install {package_name}")
    
    index_data = {
        "project_root": str(package_path),
        "last_indexed": "2024-01-01T00:00:00",
        "languages": [language],
        "files": {},
        "call_graph": {},
    }
    
    if language == "python":
        for py_file in package_path.rglob("*.py"):
            if "__pycache__" in str(py_file) or ".pyc" in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
            except:
                continue
            
            symbols = []
            for line_num, line in enumerate(content.split("\n"), 1):
                line = line.strip()
                
                if line.startswith("def "):
                    func_name = line[4:].split("(")[0].strip()
                    if func_name and not func_name.startswith("_"):
                        symbols.append({
                            "name": func_name,
                            "type": "function",
                            "line": line_num,
                            "params": [],
                        })
                
                elif line.startswith("class "):
                    class_name = line[6:].split("(")[0].strip()
                    if class_name and not class_name.startswith("_"):
                        symbols.append({
                            "name": class_name,
                            "type": "class",
                            "line": line_num,
                        })
            
            if symbols:
                rel_path = py_file.relative_to(package_path)
                index_data["files"][str(rel_path)] = {"symbols": symbols}
    
    elif language in ("javascript", "typescript"):
        for js_file in package_path.rglob("*.js"):
            try:
                content = js_file.read_text(encoding="utf-8", errors="ignore")
            except:
                continue
            
            symbols = []
            for line_num, line in enumerate(content.split("\n"), 1):
                line = line.strip()
                
                if line.startswith("function ") or line.startswith("const ") and " = " in line:
                    if "function " in line:
                        func_name = line.split("function ")[1].split("(")[0].strip()
                        sym_type = "function"
                    else:
                        func_name = line.split("const ")[1].split(" = ")[0].strip()
                        sym_type = "function"
                    
                    if func_name and not func_name.startswith("_"):
                        symbols.append({
                            "name": func_name,
                            "type": sym_type,
                            "line": line_num,
                        })
                
                elif line.startswith("class "):
                    class_name = line.split("class ")[1].split(" ")[0].strip()
                    if class_name and not class_name.startswith("_"):
                        symbols.append({
                            "name": class_name,
                            "type": "class",
                            "line": line_num,
                        })
            
            if symbols:
                rel_path = js_file.relative_to(package_path)
                index_data["files"][str(rel_path)] = {"symbols": symbols}
    
    return index_data


def handle_package_index(console: Console, package_name: str, language: str, output: str = None) -> None:
    """CLI handler for package indexing."""
    output_dir = Path(output) if output else Path.cwd() / ".cortexcode"
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(f"Indexing package {package_name}...", total=None)
        
        try:
            index_data = index_package(package_name, language, output_dir)
            
            output_dir.mkdir(parents=True, exist_ok=True)
            index_path = output_dir / "index.json"
            
            existing = {}
            if index_path.exists():
                try:
                    existing = json.loads(index_path.read_text())
                except:
                    pass
            
            for k, v in index_data.get("files", {}).items():
                if k not in existing.get("files", {}):
                    existing.setdefault("files", {})[k] = v
            
            index_path.write_text(json.dumps(existing, indent=2))
            
            console.print(f"[green]✓[/green] Indexed package: {package_name}")
            console.print(f"  Files: {len(index_data.get('files', {}))}")
            
        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print(f"[dim]Install with: pip install {package_name}[/dim]")


def handle_package_list(console: Console) -> None:
    """List available packages in site-packages/node_modules."""
    console.print("\n[bold]Python packages:[/bold]")
    site_packages = Path(sys.prefix) / "Lib" / "site-packages"
    if site_packages.exists():
        for p in sorted(site_packages.iterdir())[:20]:
            if p.is_dir() and not p.name.startswith("_"):
                console.print(f"  • {p.name}")
    
    console.print("\n[bold]JavaScript packages:[/bold]")
    node_modules = Path.cwd() / "node_modules"
    if node_modules.exists():
        for p in sorted(node_modules.iterdir())[:20]:
            if p.is_dir() and not p.name.startswith("_"):
                console.print(f"  • {p.name}")
