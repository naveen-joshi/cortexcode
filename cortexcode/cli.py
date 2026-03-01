"""CLI - Command-line interface for CortexCode."""

import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from rich import box

from cortexcode import indexer
from cortexcode.context import get_context, calculate_token_savings
from cortexcode.git_diff import get_diff_context
from cortexcode.docs import generate_all_docs
from cortexcode.watcher import start_watcher


console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="cortexcode")
def main():
    """CortexCode - Lightweight code indexing for AI assistants."""
    pass


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-o", "--output", default=".cortexcode/index.json", help="Output file path")
@click.option("-v", "--verbose", is_flag=True, help="Show verbose output")
@click.option("-w", "--watch", is_flag=True, help="Start watching after indexing")
@click.option("-i", "--incremental", is_flag=True, help="Only re-index changed files")
def index(path, output, verbose, watch, incremental):
    """Index a directory and save the code graph."""
    path = Path(path).resolve()
    output = Path(output)
    
    console.print(Panel.fit(
        f"[bold cyan]⚡ CortexCode Indexer[/bold cyan]\n"
        f"[dim]Scanning: {path}[/dim]" + (" (incremental)" if incremental else ""),
        border_style="cyan"
    ))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Indexing files...", total=None)
        
        start_time = time.time()
        index_data = indexer.index_directory(path, incremental=incremental)
        elapsed = time.time() - start_time
        
        progress.update(task, completed=True)
    
    indexer.save_index(index_data, output)
    
    file_count = len(index_data.get("files", {}))
    symbol_count = sum(len(s.get("symbols", [])) if isinstance(s, dict) else len(s) for s in index_data.get("files", {}).values())
    languages = index_data.get("languages", [])
    
    table = Table(box=box.ROUNDED, show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Files", f"[bold]{file_count}[/bold]")
    table.add_row("Symbols", f"[bold]{symbol_count}[/bold]")
    table.add_row("Languages", ", ".join(languages) if languages else "N/A")
    table.add_row("Time", f"{elapsed:.2f}s")
    table.add_row("Output", str(output))
    if incremental:
        table.add_row("Mode", "[yellow]Incremental[/yellow]")
    
    console.print()
    console.print(Panel(
        table,
        title="[bold green]✓ Indexing Complete[/bold green]",
        border_style="green"
    ))
    
    if verbose:
        _show_index_summary(index_data)
    
    if watch:
        console.print(f"\n[yellow]Starting watcher...[/yellow]")
        console.print("[dim]Press Ctrl+C to stop[/dim]")
        start_watcher(path, verbose=verbose)


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-v", "--verbose", is_flag=True, help="Show file change events")
def watch(path, verbose):
    """Watch for file changes and auto-reindex."""
    path = Path(path).resolve()
    
    console.print(f"[bold blue]Watching:[/bold blue] {path}")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    
    start_watcher(path, verbose=verbose)


@main.command()
@click.argument("query", required=False)
@click.option("-n", "--num-results", default=5, help="Number of results to return")
@click.option("-f", "--format", "output_format", default="text", type=click.Choice(["text", "json"]))
@click.option("--tokens", is_flag=True, help="Show token savings estimate")
def context(query, num_results, output_format, tokens):
    """Get relevant context for AI assistants."""
    index_path = Path(".cortexcode/index.json")
    
    if not index_path.exists():
        console.print("[bold red]Error:[/bold red] No index found. Run 'cortexcode index' first.")
        sys.exit(1)
    
    result = get_context(index_path, query, num_results)
    
    if output_format == "json":
        import json
        console.print(json.dumps(result, indent=2))
    else:
        _print_context(result)
    
    if tokens:
        savings = calculate_token_savings(index_path, query, num_results)
        _print_token_savings(savings)


@main.command()
@click.argument("query")
@click.option("-t", "--type", "sym_type", default=None, help="Filter by type (function, class, method, interface)")
@click.option("-f", "--file", "file_filter", default=None, help="Filter by file path")
@click.option("-n", "--limit", default=20, help="Max results")
def search(query, sym_type, file_filter, limit):
    """Search indexed symbols (grep-like)."""
    index_path = Path(".cortexcode/index.json")
    
    if not index_path.exists():
        console.print("[bold red]Error:[/bold red] No index found. Run 'cortexcode index' first.")
        sys.exit(1)
    
    import json as _json
    index = _json.loads(index_path.read_text(encoding="utf-8"))
    files = index.get("files", {})
    call_graph = index.get("call_graph", {})
    query_lower = query.lower()
    
    results = []
    for rel_path, file_data in files.items():
        if file_filter and file_filter.lower() not in rel_path.lower():
            continue
        
        symbols = file_data.get("symbols", []) if isinstance(file_data, dict) else file_data
        for sym in symbols:
            name = sym.get("name", "").lower()
            if query_lower in name:
                if sym_type and sym.get("type") != sym_type:
                    continue
                results.append({**sym, "file": rel_path})
    
    if not results:
        console.print(f"[yellow]No symbols matching '{query}'[/yellow]")
        return
    
    console.print(f"\n[bold]Found {len(results)} symbols matching '{query}':[/bold]\n")
    
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("Type", style="dim", width=10)
    table.add_column("Name", style="cyan")
    table.add_column("File", style="dim")
    table.add_column("Line", justify="right")
    table.add_column("Calls", style="dim")
    
    for sym in results[:limit]:
        calls = sym.get("calls", [])
        calls_str = ", ".join(calls[:3]) + ("..." if len(calls) > 3 else "") if calls else ""
        table.add_row(
            sym.get("type", "?"),
            sym.get("name", "?"),
            sym.get("file", "?"),
            str(sym.get("line", "?")),
            calls_str,
        )
    
    console.print(table)
    
    if len(results) > limit:
        console.print(f"\n[dim]Showing {limit}/{len(results)} results. Use -n to see more.[/dim]")


@main.command()
@click.option("--ref", default="HEAD", help="Git ref to compare against (default: HEAD)")
@click.option("-f", "--format", "output_format", default="text", type=click.Choice(["text", "json"]))
def diff(ref, output_format):
    """Show changed symbols since last commit (git diff-aware context)."""
    index_path = Path(".cortexcode/index.json")
    
    if not index_path.exists():
        console.print("[bold red]Error:[/bold red] No index found. Run 'cortexcode index' first.")
        sys.exit(1)
    
    result = get_diff_context(index_path, ref)
    
    if output_format == "json":
        import json as _json
        console.print(_json.dumps(result, indent=2))
        return
    
    if result["changed_files"] == 0:
        console.print("[green]No changes detected.[/green]")
        return
    
    console.print(Panel.fit(
        f"[bold cyan]Git Diff Context[/bold cyan]\n"
        f"[dim]Comparing against: {ref}[/dim]",
        border_style="cyan"
    ))
    
    console.print(f"\n[bold]{result['changed_files']}[/bold] files changed\n")
    
    # Changed symbols
    changed = result.get("changed_symbols", [])
    if changed:
        table = Table(title="Changed Symbols", box=box.SIMPLE, show_header=True)
        table.add_column("", width=3)
        table.add_column("Type", style="dim", width=10)
        table.add_column("Name", style="cyan")
        table.add_column("File", style="dim")
        table.add_column("Line", justify="right")
        
        for sym in changed:
            marker = "[red]*[/red]" if sym.get("changed") else "[dim]~[/dim]"
            table.add_row(
                marker,
                sym.get("type", "?"),
                sym.get("name", "?"),
                sym.get("file", "?"),
                str(sym.get("line", "?")),
            )
        
        console.print(table)
        console.print("[dim]  [red]*[/red] = in changed lines  [dim]~[/dim] = in changed file[/dim]\n")
    
    # Affected symbols (callers of changed code)
    affected = result.get("affected_symbols", [])
    if affected:
        console.print("[bold yellow]Potentially affected symbols:[/bold yellow]\n")
        for sym in affected:
            calls_changed = ", ".join(sym.get("calls_changed", []))
            console.print(f"  [yellow]{sym['name']}[/yellow] ({sym.get('type', '?')}) in {sym.get('file', '?')}")
            console.print(f"    [dim]calls changed: {calls_changed}[/dim]")


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-o", "--output", default=".cortexcode/docs", help="Output directory")
@click.option("--open", "open_browser", is_flag=True, help="Open HTML docs in browser")
def docs(path, output, open_browser):
    """Generate project documentation."""
    path = Path(path).resolve()
    output = Path(output)
    
    console.print(Panel.fit(
        f"[bold cyan]📄 Documentation Generator[/bold cyan]\n"
        f"[dim]Source: {path}[/dim]",
        border_style="cyan"
    ))
    
    index_path = path / ".cortexcode" / "index.json"
    if not index_path.exists():
        console.print("[bold red]Error:[/bold red] No index found. Run 'cortexcode index' first.")
        sys.exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Generating documentation...", total=None)
        generate_all_docs(index_path, output)
        progress.update(task, completed=True)
    
    console.print()
    console.print(Panel(
        f"[bold green]✓[/bold green] Documentation generated successfully!\n\n"
        f"[cyan]Output:[/cyan] {output}\n"
        f"[cyan]HTML:[/cyan] {output}/index.html\n\n"
        f"[dim]Open index.html in a browser to view interactive documentation.[/dim]",
        title="[bold]Documentation Complete[/bold]",
        border_style="green"
    ))
    
    if open_browser:
        import webbrowser
        html_path = (output / "index.html").resolve()
        webbrowser.open(f"file:///{html_path}")


def _show_index_summary(index_data: dict) -> None:
    """Show a summary table of the index."""
    table = Table(title="Index Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Files", str(len(index_data.get("files", {}))))
    table.add_row("Symbols", str(len(index_data.get("call_graph", {}))))
    table.add_row("Last Indexed", index_data.get("last_indexed", "N/A"))
    
    console.print(table)


def _print_context(result: dict) -> None:
    """Print context in human-readable format."""
    if not result.get("symbols"):
        console.print("[yellow]No matching symbols found.[/yellow]")
        return
    
    console.print("\n[bold]Relevant Symbols:[/bold]\n")
    
    for sym in result["symbols"]:
        console.print(f"  [cyan]{sym['name']}[/cyan] ({sym.get('type', 'unknown')})")
        console.print(f"    File: {sym.get('file', 'unknown')}:{sym.get('line', '?')}")
        if sym.get("params"):
            console.print(f"    Params: {', '.join(sym['params'])}")
        if sym.get("calls"):
            console.print(f"    Calls: {', '.join(sym['calls'])}")
        if sym.get("called_by"):
            console.print(f"    Called by: {', '.join(sym['called_by'])}")
        console.print()


def _print_token_savings(savings: dict) -> None:
    """Print token savings analysis."""
    console.print()
    table = Table(
        title="[bold]Token Savings Analysis[/bold]",
        box=box.ROUNDED,
        show_header=False,
    )
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")
    
    raw = savings["raw_project_tokens"]
    ctx = savings["context_tokens"]
    idx = savings["index_tokens"]
    
    table.add_row("Source files", f"{savings['file_count']} files")
    table.add_row("Raw project tokens", f"[red]{raw:,}[/red]")
    table.add_row("Full index tokens", f"[yellow]{idx:,}[/yellow]")
    table.add_row("Context query tokens", f"[green]{ctx:,}[/green]")
    table.add_row("", "")
    table.add_row("Tokens saved", f"[bold green]{savings['savings_tokens']:,}[/bold green]")
    table.add_row("Savings", f"[bold green]{savings['savings_percent']}%[/bold green]")
    table.add_row("Compression ratio", f"[bold]{savings['compression_ratio']}x[/bold]")
    
    console.print(Panel(table, border_style="green"))
    
    # Cost estimate (GPT-4 pricing ~$30/1M input tokens)
    cost_raw = raw / 1_000_000 * 30
    cost_ctx = ctx / 1_000_000 * 30
    cost_saved = cost_raw - cost_ctx
    
    if cost_saved > 0.001:
        console.print(
            f"  [dim]Estimated cost per query (GPT-4 rates):[/dim]\n"
            f"  [red]Without CortexCode:[/red] ${cost_raw:.4f}\n"
            f"  [green]With CortexCode:[/green]    ${cost_ctx:.4f}\n"
            f"  [bold green]Saved per query:[/bold green]     ${cost_saved:.4f}\n"
        )


@main.command()
def stats():
    """Show project index statistics and token savings."""
    index_path = Path(".cortexcode/index.json")
    
    if not index_path.exists():
        console.print("[bold red]Error:[/bold red] No index found. Run 'cortexcode index' first.")
        sys.exit(1)
    
    console.print(Panel.fit(
        "[bold cyan]CortexCode Stats[/bold cyan]",
        border_style="cyan"
    ))
    
    savings = calculate_token_savings(index_path)
    _print_token_savings(savings)
    
    # Also show per-query savings for common queries
    import json
    index = json.loads(index_path.read_text(encoding="utf-8"))
    call_graph = index.get("call_graph", {})
    
    # Pick top 3 symbols by call count
    top_symbols = sorted(
        call_graph.items(),
        key=lambda x: len(x[1]) if isinstance(x[1], list) else 0,
        reverse=True
    )[:3]
    
    if top_symbols:
        console.print("\n[bold]Per-Query Savings (top symbols):[/bold]\n")
        query_table = Table(box=box.SIMPLE, show_header=True)
        query_table.add_column("Query", style="cyan")
        query_table.add_column("Context Tokens", justify="right")
        query_table.add_column("vs Raw", justify="right", style="green")
        
        for name, _ in top_symbols:
            q_savings = calculate_token_savings(index_path, name, 5)
            query_table.add_row(
                name,
                f"{q_savings['context_tokens']:,}",
                f"{q_savings['savings_percent']}% saved"
            )
        
        console.print(query_table)


@main.command()
def mcp():
    """Start MCP server for AI agent integration (stdin/stdout)."""
    from cortexcode.mcp_server import run_stdio_server
    
    console.print("[dim]CortexCode MCP server started (stdin/stdout)[/dim]")
    run_stdio_server()


@main.command()
def lsp():
    """Start Language Server Protocol server (stdin/stdout)."""
    from cortexcode.lsp_server import run_lsp_server
    run_lsp_server()


@main.command(name="find")
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Max results")
def semantic_find(query, limit):
    """Semantic search — find symbols by meaning, not just name.
    
    Examples: cortexcode find "authentication handler"
              cortexcode find "database models"
              cortexcode find "user login flow"
    """
    from cortexcode.semantic_search import semantic_search
    
    index_path = Path(".cortexcode/index.json")
    if not index_path.exists():
        console.print("[bold red]Error:[/bold red] No index found. Run 'cortexcode index' first.")
        sys.exit(1)
    
    result = semantic_search(index_path, query, limit)
    results = result.get("results", [])
    
    if not results:
        console.print(f"[yellow]No results for '{query}'[/yellow]")
        return
    
    console.print(f"\n[bold]Semantic search: \"{query}\"[/bold]  ({len(results)} results from {result['total_symbols']} symbols)\n")
    
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("Score", justify="right", width=6)
    table.add_column("Type", style="dim", width=10)
    table.add_column("Name", style="cyan")
    table.add_column("File", style="dim")
    table.add_column("Line", justify="right", width=5)
    
    for r in results:
        score_color = "green" if r["score"] > 0.3 else "yellow" if r["score"] > 0.1 else "dim"
        table.add_row(
            f"[{score_color}]{r['score']:.2f}[/{score_color}]",
            r.get("type", "?"),
            r.get("name", "?"),
            r.get("file", "?"),
            str(r.get("line", "?")),
        )
    
    console.print(table)


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def scan(path):
    """Scan dependencies for known issues and security warnings."""
    from cortexcode.vuln_scan import scan_dependencies
    
    path = Path(path).resolve()
    
    console.print(Panel.fit(
        f"[bold cyan]Dependency Scanner[/bold cyan]\n"
        f"[dim]Scanning: {path}[/dim]",
        border_style="cyan"
    ))
    
    result = scan_dependencies(path)
    
    if not result["scanned_files"]:
        console.print("[yellow]No dependency files found.[/yellow]")
        return
    
    console.print(f"\n[bold]Scanned:[/bold] {', '.join(result['scanned_files'])}")
    console.print(f"[bold]Dependencies found:[/bold] {result['total_dependencies']}")
    
    warnings = result.get("warnings", [])
    if warnings:
        console.print(f"\n[bold yellow]Warnings ({len(warnings)}):[/bold yellow]\n")
        for w in warnings:
            severity_color = {"high": "red", "medium": "yellow", "low": "dim"}.get(w["severity"], "white")
            console.print(f"  [{severity_color}][{w['severity'].upper()}][/{severity_color}] {w['package']}: {w['message']}")
    else:
        console.print("\n[green]No warnings found.[/green]")


@main.command("dead-code")
@click.argument("path", default=".", type=click.Path(exists=True))
def dead_code(path):
    """Detect potentially unused symbols (dead code)."""
    from cortexcode.analysis import detect_dead_code
    
    path = Path(path).resolve()
    index_path = path / ".cortexcode" / "index.json"
    if not index_path.exists():
        console.print("[red]No index found. Run `cortexcode index` first.[/red]")
        return
    
    import json as _json
    index = _json.loads(index_path.read_text(encoding="utf-8"))
    dead = detect_dead_code(index)
    
    if not dead:
        console.print("[green]No dead code detected — all symbols are referenced.[/green]")
        return
    
    console.print(Panel.fit(
        f"[bold yellow]Potentially Unused Symbols[/bold yellow]\n"
        f"[dim]Found {len(dead)} symbols that are never called or imported[/dim]",
        border_style="yellow"
    ))
    
    table = Table(box=box.ROUNDED)
    table.add_column("Type", width=10)
    table.add_column("Name", style="cyan")
    table.add_column("File")
    table.add_column("Line", justify="right", width=5)
    
    for d in dead[:50]:
        table.add_row(d["type"], d["name"], d["file"], str(d["line"]))
    
    console.print(table)
    if len(dead) > 50:
        console.print(f"[dim]... and {len(dead) - 50} more[/dim]")


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--top", "-n", default=20, help="Show top N most complex functions")
@click.option("--min-score", default=0, help="Minimum complexity score to show")
def complexity(path, top, min_score):
    """Analyze code complexity metrics for all functions."""
    from cortexcode.analysis import compute_complexity
    
    path = Path(path).resolve()
    index_path = path / ".cortexcode" / "index.json"
    if not index_path.exists():
        console.print("[red]No index found. Run `cortexcode index` first.[/red]")
        return
    
    import json as _json
    index = _json.loads(index_path.read_text(encoding="utf-8"))
    results = compute_complexity(index, project_root=str(path))
    
    if min_score > 0:
        results = [r for r in results if r.get("score", 0) >= min_score]
    
    if not results:
        console.print("[green]No complex functions found.[/green]")
        return
    
    # Summary stats
    ratings = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for r in results:
        ratings[r.get("rating", "low")] += 1
    
    console.print(Panel.fit(
        f"[bold cyan]Complexity Analysis[/bold cyan]\n"
        f"[green]Low: {ratings['low']}[/green]  [yellow]Medium: {ratings['medium']}[/yellow]  "
        f"[red]High: {ratings['high']}[/red]  [bold red]Critical: {ratings['critical']}[/bold red]",
        border_style="cyan"
    ))
    
    table = Table(title=f"Top {top} Most Complex Functions", box=box.ROUNDED)
    table.add_column("Score", justify="right", width=6)
    table.add_column("Rating", width=8)
    table.add_column("Name", style="cyan")
    table.add_column("Lines", justify="right", width=6)
    table.add_column("CC", justify="right", width=4)
    table.add_column("Nest", justify="right", width=4)
    table.add_column("Params", justify="right", width=6)
    table.add_column("File")
    
    for r in results[:top]:
        rating = r.get("rating", "low")
        color = {"low": "green", "medium": "yellow", "high": "red", "critical": "bold red"}[rating]
        table.add_row(
            str(r.get("score", 0)),
            f"[{color}]{rating}[/{color}]",
            r["name"],
            str(r.get("lines", "?")),
            str(r.get("cyclomatic", "?")),
            str(r.get("max_nesting", "?")),
            str(r.get("params_count", 0)),
            r["file"],
        )
    
    console.print(table)


@main.command()
@click.argument("symbol")
@click.argument("path", default=".", type=click.Path(exists=True))
def impact(symbol, path):
    """Analyze change impact — what breaks if a symbol is modified."""
    from cortexcode.analysis import analyze_change_impact
    
    path = Path(path).resolve()
    index_path = path / ".cortexcode" / "index.json"
    if not index_path.exists():
        console.print("[red]No index found. Run `cortexcode index` first.[/red]")
        return
    
    import json as _json
    index = _json.loads(index_path.read_text(encoding="utf-8"))
    result = analyze_change_impact(index, symbol)
    
    risk_color = {"low": "green", "medium": "yellow", "high": "red"}[result["risk"]]
    
    console.print(Panel.fit(
        f"[bold cyan]Change Impact Analysis[/bold cyan]\n"
        f"Symbol: [bold]{symbol}[/bold]\n"
        f"Risk: [{risk_color}]{result['risk'].upper()}[/{risk_color}]  |  "
        f"Total impact: {result['total_impact']} symbols",
        border_style="cyan"
    ))
    
    if result["direct_callers"]:
        console.print(f"\n[bold]Direct callers ({len(result['direct_callers'])}):[/bold]")
        for c in result["direct_callers"]:
            console.print(f"  [cyan]{c}[/cyan]")
    
    if result["indirect_callers"]:
        console.print(f"\n[bold]Indirect callers ({len(result['indirect_callers'])}):[/bold]")
        for c in result["indirect_callers"]:
            console.print(f"  [dim]{c}[/dim]")
    
    if result["affected_files"]:
        console.print(f"\n[bold]Affected files ({len(result['affected_files'])}):[/bold]")
        for f in result["affected_files"]:
            console.print(f"  {f}")
    
    if result["affected_tests"]:
        console.print(f"\n[bold yellow]Tests to update ({len(result['affected_tests'])}):[/bold yellow]")
        for f in result["affected_tests"]:
            console.print(f"  {f}")
    
    if result["importing_files"]:
        console.print(f"\n[bold]Files importing affected modules ({len(result['importing_files'])}):[/bold]")
        for f in result["importing_files"]:
            console.print(f"  [dim]{f}[/dim]")


@main.group()
def workspace():
    """Multi-repo workspace management."""
    pass


@workspace.command("init")
@click.argument("path", default=".", type=click.Path(exists=True))
def workspace_init(path):
    """Initialize a workspace at the given path."""
    from cortexcode.workspace import Workspace
    
    ws = Workspace(Path(path).resolve())
    if ws.load_config():
        console.print("[yellow]Workspace already exists here.[/yellow]")
        return
    ws.save_config()
    console.print(f"[green]Workspace initialized at {ws.workspace_root}[/green]")


@workspace.command("add")
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("--alias", "-a", default=None, help="Short alias for the repo")
def workspace_add(repo_path, alias):
    """Add a repo to the workspace."""
    from cortexcode.workspace import Workspace
    
    ws = Workspace(Path(".").resolve())
    if not ws.load_config():
        console.print("[red]No workspace found. Run `cortexcode workspace init` first.[/red]")
        return
    try:
        repo = ws.add_repo(repo_path, alias)
        console.print(f"[green]Added {repo['alias']} → {repo['path']}[/green]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


@workspace.command("remove")
@click.argument("alias_or_path")
def workspace_remove(alias_or_path):
    """Remove a repo from the workspace."""
    from cortexcode.workspace import Workspace
    
    ws = Workspace(Path(".").resolve())
    if not ws.load_config():
        console.print("[red]No workspace found.[/red]")
        return
    if ws.remove_repo(alias_or_path):
        console.print(f"[green]Removed {alias_or_path}[/green]")
    else:
        console.print(f"[yellow]Not found: {alias_or_path}[/yellow]")


@workspace.command("list")
def workspace_list():
    """List all repos in the workspace."""
    from cortexcode.workspace import Workspace
    
    ws = Workspace(Path(".").resolve())
    if not ws.load_config():
        console.print("[red]No workspace found. Run `cortexcode workspace init` first.[/red]")
        return
    
    repos = ws.list_repos()
    if not repos:
        console.print("[dim]No repos in workspace. Use `cortexcode workspace add <path>`[/dim]")
        return
    
    table = Table(title="Workspace Repos", box=box.ROUNDED)
    table.add_column("Alias", style="cyan")
    table.add_column("Path")
    table.add_column("Indexed", justify="center")
    
    for r in repos:
        table.add_row(r["alias"], r["path"], "✓" if r["indexed"] else "✗")
    console.print(table)


@workspace.command("index")
@click.option("--full", is_flag=True, help="Full re-index (not incremental)")
def workspace_index(full):
    """Index all repos in the workspace."""
    from cortexcode.workspace import Workspace
    
    ws = Workspace(Path(".").resolve())
    if not ws.load_config():
        console.print("[red]No workspace found.[/red]")
        return
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task("Indexing workspace repos...", total=None)
        results = ws.index_all(incremental=not full)
    
    table = Table(title="Workspace Index Results", box=box.ROUNDED)
    table.add_column("Repo", style="cyan")
    table.add_column("Symbols", justify="right")
    
    for alias, count in results.items():
        color = "green" if count >= 0 else "red"
        table.add_row(alias, f"[{color}]{count}[/{color}]")
    console.print(table)


@workspace.command("search")
@click.argument("query")
def workspace_search(query):
    """Search symbols across all workspace repos."""
    from cortexcode.workspace import Workspace
    
    ws = Workspace(Path(".").resolve())
    if not ws.load_config():
        console.print("[red]No workspace found.[/red]")
        return
    
    results = ws.search_across_repos(query)
    if not results:
        console.print(f"[dim]No results for '{query}'[/dim]")
        return
    
    table = Table(title=f"Results for '{query}'", box=box.ROUNDED)
    table.add_column("Repo", style="dim", width=12)
    table.add_column("Type", width=10)
    table.add_column("Name", style="cyan")
    table.add_column("File")
    
    for r in results:
        table.add_row(r.get("repo", "?"), r.get("type", "?"), r.get("name", "?"), r.get("file", "?"))
    console.print(table)


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--port", "-p", default=8787, help="Port to serve the dashboard")
def dashboard(path, port):
    """Launch a live web dashboard with auto-refresh on index changes."""
    from cortexcode.dashboard import DashboardServer
    
    path = Path(path).resolve()
    index_path = path / ".cortexcode" / "index.json"
    
    if not index_path.exists():
        console.print("[yellow]No index found. Indexing first...[/yellow]")
        idx = indexer.CodeIndexer()
        index = idx.index_directory(path)
        output_dir = path / ".cortexcode"
        output_dir.mkdir(exist_ok=True)
        import json as _json
        index_path.write_text(_json.dumps(index, indent=2, default=str), encoding="utf-8")
    
    docs_dir = path / ".cortexcode" / "docs"
    console.print(Panel.fit(
        f"[bold cyan]CortexCode Live Dashboard[/bold cyan]\n"
        f"[dim]Serving: {docs_dir}[/dim]\n"
        f"[bold green]http://localhost:{port}[/bold green]\n"
        f"[dim]Auto-refreshes when index changes[/dim]",
        border_style="cyan"
    ))
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    
    server = DashboardServer(path, port)
    server.start(open_browser=True)


if __name__ == "__main__":
    main()
