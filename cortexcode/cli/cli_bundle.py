"""Bundle management - export/import pre-indexed code graphs."""

import gzip
import json
import shutil
import zipfile
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn


BUNDLE_VERSION = "1.0"


def export_bundle(index_path: Path, output_path: Path, name: str = None) -> Path:
    """Export index as a shareable bundle."""
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found at {index_path}")

    with open(index_path) as f:
        index_data = json.load(f)

    bundle_name = name or index_data.get("project_root", "project")
    bundle_name = Path(bundle_name).name

    bundle_data = {
        "version": BUNDLE_VERSION,
        "name": bundle_name,
        "exported": str(Path.cwd()),
        "index": index_data,
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not output_path.suffix:
        output_path = output_path / f"{bundle_name}.ccb"

    with gzip.open(output_path, "wt", encoding="utf-8") as f:
        json.dump(bundle_data, f)

    return output_path


def import_bundle(bundle_path: Path, output_dir: Path) -> Path:
    """Import a bundle and return the index path."""
    with gzip.open(bundle_path, "rt", encoding="utf-8") as f:
        bundle_data = json.load(f)

    if bundle_data.get("version") != BUNDLE_VERSION:
        raise ValueError(f"Unsupported bundle version: {bundle_data.get('version')}")

    index_data = bundle_data["index"]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    index_path = output_dir / "index.json"
    with open(index_path, "w") as f:
        json.dump(index_data, f, indent=2)

    return index_path


def list_bundle_info(bundle_path: Path) -> dict:
    """Get info about a bundle without importing it."""
    with gzip.open(bundle_path, "rt", encoding="utf-8") as f:
        bundle_data = json.load(f)

    index = bundle_data.get("index", {})
    files = index.get("files", {})
    symbols = sum(len(f.get("symbols", [])) for f in files.values())

    return {
        "name": bundle_data.get("name"),
        "version": bundle_data.get("version"),
        "exported_from": bundle_data.get("exported"),
        "files": len(files),
        "symbols": symbols,
    }


def handle_bundle_export(console: Console, path: str, output: str, name: str = None) -> None:
    """CLI handler for bundle export."""
    path = Path(path)
    index_path = path / ".cortexcode" / "index.json"

    if not index_path.exists():
        console.print(f"[red]No index found at {index_path}[/red]")
        console.print("Run [cyan]cortexcode index[/cyan] first")
        return

    output_path = Path(output) if output else Path.cwd()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Exporting bundle...", total=None)
        result = export_bundle(index_path, output_path, name)

    size_kb = result.stat().st_size / 1024
    console.print(f"[green]✓[/green] Bundle exported: {result} ({size_kb:.1f} KB)")


def handle_bundle_import(console: Console, bundle_path: str, output: str = None) -> None:
    """CLI handler for bundle import."""
    bundle_path = Path(bundle_path)

    if not bundle_path.exists():
        console.print(f"[red]Bundle not found: {bundle_path}[/red]")
        return

    output_dir = Path(output) if output else Path.cwd() / ".cortexcode"

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Importing bundle...", total=None)
        result = import_bundle(bundle_path, output_dir)

    console.print(f"[green]✓[/green] Bundle imported: {result}")


def handle_bundle_info(console: Console, bundle_path: str) -> None:
    """CLI handler for bundle info."""
    bundle_path = Path(bundle_path)

    if not bundle_path.exists():
        console.print(f"[red]Bundle not found: {bundle_path}[/red]")
        return

    info = list_bundle_info(bundle_path)

    console.print(f"\n[bold cyan]Bundle: {info['name']}[/bold cyan]")
    console.print(f"  Version:    {info['version']}")
    console.print(f"  Exported:   {info['exported_from']}")
    console.print(f"  Files:      {info['files']}")
    console.print(f"  Symbols:    {info['symbols']}")
