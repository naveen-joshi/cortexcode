from pathlib import Path

from rich import box
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table


def handle_workspace_init(console: Console, path, Workspace) -> None:
    workspace = Workspace(Path(path).resolve())
    if workspace.load_config():
        console.print("[yellow]Workspace already exists here.[/yellow]")
        return
    workspace.save_config()
    console.print(f"[green]Workspace initialized at {workspace.workspace_root}[/green]")


def handle_workspace_add(console: Console, repo_path, alias, Workspace) -> None:
    workspace = Workspace(Path(".").resolve())
    if not workspace.load_config():
        console.print("[red]No workspace found. Run `cortexcode workspace init` first.[/red]")
        return

    try:
        repo = workspace.add_repo(repo_path, alias)
        console.print(f"[green]Added {repo['alias']} → {repo['path']}[/green]")
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")


def handle_workspace_remove(console: Console, alias_or_path, Workspace) -> None:
    workspace = Workspace(Path(".").resolve())
    if not workspace.load_config():
        console.print("[red]No workspace found.[/red]")
        return

    if workspace.remove_repo(alias_or_path):
        console.print(f"[green]Removed {alias_or_path}[/green]")
    else:
        console.print(f"[yellow]Not found: {alias_or_path}[/yellow]")


def handle_workspace_list(console: Console, Workspace) -> None:
    workspace = Workspace(Path(".").resolve())
    if not workspace.load_config():
        console.print("[red]No workspace found. Run `cortexcode workspace init` first.[/red]")
        return

    repos = workspace.list_repos()
    if not repos:
        console.print("[dim]No repos in workspace. Use `cortexcode workspace add <path>`[/dim]")
        return

    table = Table(title="Workspace Repos", box=box.ROUNDED)
    table.add_column("Alias", style="cyan")
    table.add_column("Path")
    table.add_column("Indexed", justify="center")

    for repo in repos:
        table.add_row(repo["alias"], repo["path"], "✓" if repo["indexed"] else "✗")
    console.print(table)


def handle_workspace_index(console: Console, full: bool, Workspace) -> None:
    workspace = Workspace(Path(".").resolve())
    if not workspace.load_config():
        console.print("[red]No workspace found.[/red]")
        return

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task("Indexing workspace repos...", total=None)
        results = workspace.index_all(incremental=not full)

    table = Table(title="Workspace Index Results", box=box.ROUNDED)
    table.add_column("Repo", style="cyan")
    table.add_column("Symbols", justify="right")

    for alias, count in results.items():
        color = "green" if count >= 0 else "red"
        table.add_row(alias, f"[{color}]{count}[/{color}]")
    console.print(table)


def handle_workspace_search(console: Console, query: str, Workspace) -> None:
    workspace = Workspace(Path(".").resolve())
    if not workspace.load_config():
        console.print("[red]No workspace found.[/red]")
        return

    results = workspace.search_across_repos(query)
    if not results:
        console.print(f"[dim]No results for '{query}'[/dim]")
        return

    table = Table(title=f"Results for '{query}'", box=box.ROUNDED)
    table.add_column("Repo", style="dim", width=12)
    table.add_column("Type", width=10)
    table.add_column("Name", style="cyan")
    table.add_column("File")

    for result in results:
        table.add_row(result.get("repo", "?"), result.get("type", "?"), result.get("name", "?"), result.get("file", "?"))
    console.print(table)
