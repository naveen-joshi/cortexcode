import time
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeRemainingColumn
from rich.table import Table


def handle_index_command(
    console: Console,
    path: str | Path,
    output: str | Path,
    verbose: bool,
    watch: bool,
    incremental: bool,
    include_tests,
    exclude,
    include,
    root,
    dry_run: bool,
    indexer_module,
    print_index_header,
    print_project_profile_summary,
    show_index_summary,
    start_watcher,
) -> None:
    path = Path(path).resolve()
    output = Path(output)

    from cortexcode.config import get_filter_opts_from_config

    print_index_header(console, path, incremental)

    config_filter_opts = get_filter_opts_from_config(path)
    filter_opts = {
        "include_tests": include_tests if include_tests is not None else config_filter_opts.get("include_tests", False),
        "max_file_size": config_filter_opts.get("max_file_size", 1024 * 1024),
        "exclude_patterns": list(exclude) if exclude else config_filter_opts.get("exclude_patterns", []),
        "include_patterns": list(include) if include else config_filter_opts.get("include_patterns", []),
        "monorepo_root": root or config_filter_opts.get("monorepo_root"),
    }

    if dry_run:
        from cortexcode.performance import preview_indexing

        preview = preview_indexing(path, filter_opts)
        console.print(Panel(
            f"[bold]Files to index:[/bold] {preview['files_to_index']}\n"
            f"[bold]Files to skip:[/bold] {preview['files_to_skip']}\n\n"
            f"[dim]Skip reasons:[/dim]\n"
            f"  - File too large: {preview['skip_reasons']['file_too_large']}\n"
            f"  - Ignored: {preview['skip_reasons']['ignored']}\n\n"
            f"[bold]Sample files that would be indexed:[/bold]\n" +
            "\n".join(f"  - {f}" for f in preview['sample_files'][:10]),
            title="[bold]Dry Run Preview[/bold]",
            border_style="yellow",
        ))
        return

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
        index_data = indexer_module.index_directory(path, incremental=incremental, filter_opts=filter_opts)
        elapsed = time.time() - start_time

        progress.update(task, completed=True)

    indexer_module.save_index(index_data, output)

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
        border_style="green",
    ))
    print_project_profile_summary(console, index_data)

    if verbose:
        show_index_summary(console, index_data)

    if watch:
        console.print("\n[yellow]Starting watcher...[/yellow]")
        console.print("[dim]Press Ctrl+C to stop[/dim]")
        start_watcher(path, verbose=verbose)
