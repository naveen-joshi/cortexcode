from pathlib import Path

from rich import box
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table


def _load_or_warn(console: Console, Workspace):
    """Load workspace via discovery, falling back to CWD. Returns ws or None."""
    ws = Workspace.discover()
    if ws:
        return ws
    ws = Workspace(Path(".").resolve())
    if ws.load_config():
        return ws
    console.print("[red]No workspace found. Run `cortexcode workspace init` first.[/red]")
    return None


def handle_workspace_init(console: Console, path, Workspace) -> None:
    workspace = Workspace(Path(path).resolve())
    if workspace.load_config():
        console.print("[yellow]Workspace already exists here.[/yellow]")
        return
    workspace.save_config()
    console.print(f"[green]Workspace initialized at {workspace.workspace_root}[/green]")
    console.print(f"[dim]Config: {workspace._config_path}[/dim]")


def handle_workspace_add(console: Console, repo_path, alias, Workspace) -> None:
    workspace = _load_or_warn(console, Workspace)
    if not workspace:
        return
    try:
        repo = workspace.add_repo(repo_path, alias)
        msg = f"[green]Added {repo['id']} → {repo['path']}[/green]"
        if repo.get("package"):
            msg += f"  [dim](package: {repo['package']})[/dim]"
        console.print(msg)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")


def handle_workspace_remove(console: Console, alias_or_path, Workspace) -> None:
    workspace = _load_or_warn(console, Workspace)
    if not workspace:
        return
    if workspace.remove_repo(alias_or_path):
        console.print(f"[green]Removed {alias_or_path}[/green]")
    else:
        console.print(f"[yellow]Not found: {alias_or_path}[/yellow]")


def handle_workspace_list(console: Console, Workspace) -> None:
    workspace = _load_or_warn(console, Workspace)
    if not workspace:
        return

    repos = workspace.list_repos()
    if not repos:
        console.print("[dim]No repos in workspace. Use `cortexcode workspace add <path>`[/dim]")
        return

    table = Table(title=f"Workspace: {workspace.name}", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("Package", style="magenta")
    table.add_column("Path")
    table.add_column("Indexed", justify="center")

    for repo in repos:
        table.add_row(
            repo["id"],
            repo.get("package") or "[dim]—[/dim]",
            repo["path"],
            "✓" if repo["indexed"] else "✗",
        )
    console.print(table)


def handle_workspace_index(console: Console, full: bool, Workspace) -> None:
    workspace = _load_or_warn(console, Workspace)
    if not workspace:
        return

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task("Indexing workspace repos and building linkage...", total=None)
        results = workspace.index_all(incremental=not full)

    table = Table(title="Workspace Index Results", box=box.ROUNDED)
    table.add_column("Repo", style="cyan")
    table.add_column("Symbols", justify="right")

    for repo_id, count in results.items():
        color = "green" if count >= 0 else "red"
        table.add_row(repo_id, f"[{color}]{count}[/{color}]")
    console.print(table)

    linkage = workspace.load_linkage() or {}
    edge_count = len(linkage.get("package_edges", []))
    console.print(f"[dim]Linkage: {edge_count} cross-repo package edge(s)[/dim]")


def handle_workspace_search(console: Console, query: str, Workspace) -> None:
    workspace = _load_or_warn(console, Workspace)
    if not workspace:
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
    table.add_column("Line", justify="right")

    for result in results:
        table.add_row(
            result.get("repo", "?"),
            result.get("type", "?"),
            result.get("name", "?"),
            result.get("file", "?"),
            str(result.get("line", "")),
        )
    console.print(table)


def handle_workspace_impact(console: Console, ref: str, Workspace) -> None:
    workspace = _load_or_warn(console, Workspace)
    if not workspace:
        return

    result = workspace.impact(ref)
    if "error" in result:
        console.print(f"[red]{result['error']}[/red]")
        return

    local = result["local"]
    console.print(f"[bold]Impact for [cyan]{ref}[/cyan][/bold]")
    console.print(f"[dim]Repo:[/dim] {local['repo']}  [dim]Kind:[/dim] {local['kind']}  [dim]Target:[/dim] {local['target']}")

    if local["kind"] == "symbol":
        callers = local["callers"]
        if callers:
            table = Table(title="Local callers", box=box.SIMPLE)
            table.add_column("Caller", style="cyan")
            for c in callers:
                table.add_row(c)
            console.print(table)
        else:
            console.print("[dim]No local callers in call graph.[/dim]")
    else:
        affected = local["files_affected"]
        if affected:
            table = Table(title="Files importing this file", box=box.SIMPLE)
            table.add_column("File", style="cyan")
            for f in affected:
                table.add_row(f)
            console.print(table)
        else:
            console.print("[dim]No local importers.[/dim]")

    consumers = result.get("consumers", [])
    if not consumers:
        console.print("[dim]No cross-repo consumers via package edges.[/dim]")
        return

    cross = result.get("cross_repo", [])
    if not cross:
        console.print(f"[dim]Linked consumers ({', '.join(consumers)}) — no symbol references found.[/dim]")
        return

    for entry in cross:
        table = Table(title=f"Cross-repo references in [cyan]{entry['repo']}[/cyan] ({entry['hit_count']} file(s))", box=box.ROUNDED)
        table.add_column("File", style="cyan")
        table.add_column("Imports")
        table.add_column("Calls")
        for hit in entry["hits"]:
            table.add_row(
                hit["file"],
                ", ".join(str(i) for i in hit["imports"]) or "[dim]—[/dim]",
                ", ".join(hit["calls"]) or "[dim]—[/dim]",
            )
        console.print(table)


def handle_workspace_deps(console: Console, Workspace) -> None:
    workspace = _load_or_warn(console, Workspace)
    if not workspace:
        return

    deps = workspace.cross_repo_deps()
    graph = deps["graph"]
    edges = deps["edges"]

    if not edges:
        console.print("[dim]No cross-repo dependencies detected.[/dim]")
        console.print("[dim]Tip: ensure each repo's `package` field matches the dependency name in consumer manifests.[/dim]")
        return

    table = Table(title=f"Cross-repo dependencies — {workspace.name}", box=box.ROUNDED)
    table.add_column("From", style="cyan")
    table.add_column("→ To", style="magenta")
    table.add_column("Package")
    table.add_column("Manifest", style="dim")
    for edge in edges:
        table.add_row(edge["from_repo"], edge["to_repo"], edge["package"], edge.get("manifest", ""))
    console.print(table)

    console.print()
    summary = Table(title="Repo dependency summary", box=box.SIMPLE)
    summary.add_column("Repo", style="cyan")
    summary.add_column("Depends on")
    for repo_id, targets in graph.items():
        summary.add_row(repo_id, ", ".join(targets) if targets else "[dim]—[/dim]")
    console.print(summary)


def handle_workspace_linkage(console: Console, Workspace) -> None:
    workspace = _load_or_warn(console, Workspace)
    if not workspace:
        return

    linkage = workspace.load_linkage()
    if not linkage:
        console.print("[yellow]No linkage cache found. Run `cortexcode workspace index` first.[/yellow]")
        return

    console.print(f"[bold]Linkage for [cyan]{linkage.get('workspace')}[/cyan][/bold]")
    console.print(f"[dim]Built: {linkage.get('built_at')}[/dim]")
    console.print(f"[dim]Cache: {workspace.linkage_path()}[/dim]")
    edges = linkage.get("package_edges", [])
    console.print(f"[dim]Package edges: {len(edges)}[/dim]")

    if edges:
        table = Table(box=box.SIMPLE)
        table.add_column("From", style="cyan")
        table.add_column("To", style="magenta")
        table.add_column("Via")
        table.add_column("Package")
        table.add_column("Manifest", style="dim")
        for e in edges:
            table.add_row(e["from_repo"], e["to_repo"], e.get("via", ""), e["package"], e.get("manifest", ""))
        console.print(table)
