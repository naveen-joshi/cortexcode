from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


FRONTEND_FRAMEWORKS = {"react", "react-native", "nextjs", "angular", "expo", "flutter", "swiftui", "uikit", "remix"}


def show_index_summary(console: Console, index_data: dict[str, Any]) -> None:
    table = Table(title="Index Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Files", str(len(index_data.get("files", {}))))
    table.add_row("Symbols", str(len(index_data.get("call_graph", {}))))
    table.add_row("Last Indexed", index_data.get("last_indexed", "N/A"))

    console.print(table)


def get_available_reports(index_data: dict[str, Any], report_types: list[str]) -> list[str]:
    profile = index_data.get("project_profile", {})
    recommended = profile.get("recommendations", {}).get("reports", [])
    ordered = [report_name for report_name in report_types if report_name in recommended]
    fallback = [report_name for report_name in report_types if report_name not in ordered]
    return ordered + fallback[:3] if ordered else ["overview", "tech", "hotspots", "routes", "entities"]


def print_project_profile_summary(console: Console, index_data: dict[str, Any]) -> None:
    profile = index_data.get("project_profile", {})
    if not profile:
        return

    frameworks = profile.get("frameworks", [])[:4]
    layers = profile.get("layers", [])[:4]
    recommendations = profile.get("recommendations", {})

    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("Key", style="cyan", width=18)
    table.add_column("Value", style="white")
    table.add_row("Frameworks", ", ".join(f"{item.get('name')} ({item.get('count')})" for item in frameworks) if frameworks else "None detected")
    table.add_row("Layers", ", ".join(f"{item.get('name')} ({item.get('files')} files)" for item in layers) if layers else "None inferred")
    table.add_row("Runtime surface", f"{profile.get('route_count', 0)} routes, {profile.get('entity_count', 0)} entities")
    table.add_row("Suggested reports", ", ".join(recommendations.get("reports", [])[:5]) or "overview, tech, hotspots")
    table.add_row("Suggested diagrams", ", ".join(recommendations.get("diagrams", [])[:5]) or "architecture, call_graph")

    console.print()
    console.print(Panel(table, title="[bold]Detected Project Shape[/bold]", border_style="cyan"))


def print_terminal_report(console: Console, report_type: str, index_data: dict[str, Any], path: Path) -> None:
    profile = index_data.get("project_profile", {})
    hotspots = profile.get("hotspots", {})
    console.print(Panel.fit(f"[bold cyan]{report_type.title()} Report[/bold cyan]\n[dim]Source: {path}[/dim]", border_style="cyan"))

    if report_type == "overview":
        summary = Table(box=box.SIMPLE, show_header=False)
        summary.add_column("Key", style="cyan", width=18)
        summary.add_column("Value", style="white")
        summary.add_row("Files", str(len(index_data.get("files", {}))))
        summary.add_row("Languages", ", ".join(index_data.get("languages", [])) or "N/A")
        summary.add_row("Frameworks", ", ".join(item.get("name", "unknown") for item in profile.get("frameworks", [])[:6]) or "None")
        summary.add_row("Entry points", str(len(profile.get("entry_points", []))))
        summary.add_row("Routes", str(profile.get("route_count", 0)))
        summary.add_row("Entities", str(profile.get("entity_count", 0)))
        console.print(summary)
        print_project_profile_summary(console, index_data)
        return

    if report_type == "tech":
        framework_table = Table(title="Detected Frameworks", box=box.SIMPLE)
        framework_table.add_column("Framework", style="cyan")
        framework_table.add_column("Signals", justify="right")
        for item in profile.get("frameworks", [])[:10]:
            framework_table.add_row(item.get("name", "unknown"), str(item.get("count", 0)))
        if framework_table.row_count:
            console.print(framework_table)

        layer_table = Table(title="Architecture Layers", box=box.SIMPLE)
        layer_table.add_column("Layer", style="cyan")
        layer_table.add_column("Files", justify="right")
        layer_table.add_column("Symbols", justify="right")
        layer_table.add_column("Routes", justify="right")
        layer_table.add_column("Entities", justify="right")
        for layer in profile.get("layers", []):
            layer_table.add_row(
                layer.get("name", "unknown"),
                str(layer.get("files", 0)),
                str(layer.get("symbols", 0)),
                str(layer.get("routes", 0)),
                str(layer.get("entities", 0)),
            )
        if layer_table.row_count:
            console.print(layer_table)
        return

    if report_type == "hotspots":
        fan_out_table = Table(title="Hotspots by Fan-out", box=box.SIMPLE)
        fan_out_table.add_column("Symbol", style="cyan")
        fan_out_table.add_column("Calls", justify="right")
        for item in hotspots.get("fan_out", [])[:10]:
            fan_out_table.add_row(item.get("name", "unknown"), str(item.get("count", 0)))
        if fan_out_table.row_count:
            console.print(fan_out_table)

        fan_in_table = Table(title="Hotspots by Fan-in", box=box.SIMPLE)
        fan_in_table.add_column("Symbol", style="cyan")
        fan_in_table.add_column("Callers", justify="right")
        for item in hotspots.get("fan_in", [])[:10]:
            fan_in_table.add_row(item.get("name", "unknown"), str(item.get("count", 0)))
        if fan_in_table.row_count:
            console.print(fan_in_table)

        files_table = Table(title="Largest Files", box=box.SIMPLE)
        files_table.add_column("File", style="cyan")
        files_table.add_column("Role")
        files_table.add_column("Symbols", justify="right")
        for item in hotspots.get("top_files", [])[:10]:
            files_table.add_row(item.get("file", "unknown"), item.get("role", "core"), str(item.get("symbols", 0)))
        if files_table.row_count:
            console.print(files_table)
        return

    if report_type == "routes":
        route_table = Table(title="API Routes", box=box.SIMPLE)
        route_table.add_column("Method", style="cyan", width=8)
        route_table.add_column("Path", style="white")
        route_table.add_column("Framework")
        route_table.add_column("File", style="dim")
        for route in profile.get("route_samples", []):
            route_table.add_row(
                str(route.get("method", "UNKNOWN")),
                str(route.get("path", "/")),
                str(route.get("framework", "unknown")),
                str(route.get("file", "unknown")),
            )
        if route_table.row_count:
            console.print(route_table)
        else:
            console.print("[yellow]No API routes detected.[/yellow]")
        return

    if report_type == "entities":
        entity_table = Table(title="Entities", box=box.SIMPLE)
        entity_table.add_column("Entity", style="cyan")
        entity_table.add_column("Type")
        entity_table.add_column("Fields", justify="right")
        entity_table.add_column("File", style="dim")
        for entity in profile.get("entity_samples", []):
            fields = entity.get("fields", []) if isinstance(entity.get("fields"), list) else []
            entity_table.add_row(
                str(entity.get("name", "unknown")),
                str(entity.get("type", "unknown")),
                str(len(fields)),
                str(entity.get("file", "unknown")),
            )
        if entity_table.row_count:
            console.print(entity_table)
        else:
            console.print("[yellow]No entities detected.[/yellow]")
        return

    if report_type == "frontend":
        frontend_frameworks = [
            item for item in profile.get("frameworks", [])
            if item.get("name") in FRONTEND_FRAMEWORKS
        ]
        frontend_layers = [layer for layer in profile.get("layers", []) if layer.get("name") == "ui"]
        if frontend_frameworks:
            table = Table(title="Frontend Frameworks", box=box.SIMPLE)
            table.add_column("Framework", style="cyan")
            table.add_column("Signals", justify="right")
            for item in frontend_frameworks:
                table.add_row(item.get("name", "unknown"), str(item.get("count", 0)))
            console.print(table)
        if frontend_layers:
            table = Table(title="UI Layer", box=box.SIMPLE)
            table.add_column("Files", justify="right")
            table.add_column("Symbols", justify="right")
            for layer in frontend_layers:
                table.add_row(str(layer.get("files", 0)), str(layer.get("symbols", 0)))
            console.print(table)
        if not frontend_frameworks and not frontend_layers:
            console.print("[yellow]No frontend-specific signals detected.[/yellow]")
        return

    if report_type == "cli":
        cli_layers = [layer for layer in profile.get("layers", []) if layer.get("name") == "cli"]
        cli_files = [item for item in hotspots.get("top_files", []) if item.get("role") == "cli"]
        if cli_layers:
            table = Table(title="CLI Layer", box=box.SIMPLE)
            table.add_column("Files", justify="right")
            table.add_column("Symbols", justify="right")
            for layer in cli_layers:
                table.add_row(str(layer.get("files", 0)), str(layer.get("symbols", 0)))
            console.print(table)
        if cli_files:
            table = Table(title="Key CLI Files", box=box.SIMPLE)
            table.add_column("File", style="cyan")
            table.add_column("Symbols", justify="right")
            for item in cli_files:
                table.add_row(item.get("file", "unknown"), str(item.get("symbols", 0)))
            console.print(table)
        if not cli_layers and not cli_files:
            console.print("[yellow]No CLI-focused signals detected.[/yellow]")
