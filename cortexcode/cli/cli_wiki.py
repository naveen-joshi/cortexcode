"""CLI handler for the wiki command — generate CodeWiki-style documentation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn


def _ensure_api_key(console: Console, provider: str) -> Optional[str]:
    """Check for an API key and prompt the user to enter one if missing.

    Returns the API key or None if the user declines.
    """
    from cortexcode.ai_docs.config import get_api_key, set_api_key

    existing = get_api_key(provider)
    if existing:
        return existing

    provider_labels = {
        "google": ("Gemini", "https://aistudio.google.com/apikey"),
        "openai": ("OpenAI", "https://platform.openai.com/api-keys"),
        "anthropic": ("Anthropic", "https://console.anthropic.com/settings/keys"),
    }
    label, url = provider_labels.get(provider, (provider, ""))

    console.print(
        f"\n[yellow]⚠  No API key found for {label}.[/yellow]\n"
        f"[dim]Get your key at:[/dim] [cyan]{url}[/cyan]\n"
    )

    api_key = click.prompt(
        f"Enter your {label} API key (or press Enter to skip)",
        default="",
        show_default=False,
    ).strip()

    if not api_key:
        console.print("[dim]Skipped. You can set it later with:[/dim]")
        console.print(f"  [cyan]cortexcode config set {provider}_api_key YOUR_KEY[/cyan]\n")
        return None

    set_api_key(provider, api_key)
    console.print(f"[green]✓[/green] API key saved for {label}.\n")
    return api_key


def handle_wiki_command(
    console: Console,
    path: str | Path,
    output: str | Path,
    provider: str | None,
    model: str | None,
    pages: tuple[str, ...] | None,
    no_modules: bool,
    max_modules: int,
    open_browser: bool,
) -> None:
    """Generate a CodeWiki-style documentation site."""
    from cortexcode.knowledge.build import build_knowledge_pack
    from cortexcode.ai_docs.config import get_config
    from cortexcode.ai_docs.report_runner import ReportRunner
    from cortexcode.reports.site.generator import generate_wiki_site

    project_path = Path(path).resolve()
    index_path = project_path / ".cortexcode" / "index.json"

    if not index_path.exists():
        console.print(
            "[bold red]Error:[/bold red] No index found. "
            "Run [cyan]cortexcode index[/cyan] first."
        )
        return

    # Resolve provider and ensure API key
    resolved_provider = provider or get_config().provider
    api_key = _ensure_api_key(console, resolved_provider)
    if not api_key:
        console.print("[bold red]Cannot generate wiki without an API key.[/bold red]")
        return

    output_dir = Path(output)
    if not output_dir.is_absolute():
        output_dir = project_path / output_dir

    console.print(Panel.fit(
        f"[bold cyan]CortexCode Wiki Generator[/bold cyan]\n"
        f"[dim]Project:[/dim]  {project_path}\n"
        f"[dim]Output:[/dim]   {output_dir}\n"
        f"[dim]Provider:[/dim] {resolved_provider}",
        border_style="cyan",
    ))

    # Phase 1: Build knowledge pack
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Building knowledge pack...", total=None)
        pack = build_knowledge_pack(index_path)
        progress.update(task, description=f"Knowledge pack ready — {pack.symbol_count} symbols, {len(pack.concepts)} concepts")
        progress.stop()

    console.print(f"  [green]✓[/green] {pack.file_count} files, {pack.symbol_count} symbols, {pack.call_edge_count} call edges")
    console.print(f"  [green]✓[/green] {len(pack.concepts)} concepts detected: {', '.join(c.name.replace('_', ' ') for c in pack.concepts[:6])}")

    # Phase 2: Generate documentation pages
    runner = ReportRunner(provider=resolved_provider, model=model, api_key=api_key)

    page_list = list(pages) if pages else None

    def on_page_start(page_id: str, title: str) -> None:
        console.print(f"  [cyan]⟳[/cyan] Generating: {title}...")

    def on_page_done(page_id: str, status: str, usage) -> None:
        if status == "cached":
            console.print(f"    [yellow]↻[/yellow] Cached")
        elif status == "generated":
            tokens = usage.total_tokens if usage else 0
            console.print(f"    [green]✓[/green] Done ({tokens:,} tokens)")
        elif status == "error":
            console.print(f"    [red]✗[/red] Error")

    results = runner.generate_wiki(
        pack=pack,
        output_dir=output_dir,
        pages=page_list,
        include_modules=not no_modules,
        max_modules=max_modules,
        on_page_start=on_page_start,
        on_page_done=on_page_done,
    )

    # Phase 3: Generate the HTML wiki site
    generated_page_files = {}
    for page_meta in results:
        generated_page_files[page_meta.page_id] = page_meta.output_file

    console.print(f"\n  [cyan]⟳[/cyan] Building wiki site...")
    site_path = generate_wiki_site(pack, output_dir, generated_page_files)
    console.print(f"  [green]✓[/green] Wiki site generated: {site_path}")

    # Show usage summary
    usage_summary = runner.get_usage_summary()
    console.print(f"\n{usage_summary}")

    # Show output info
    console.print(Panel.fit(
        f"[bold green]✓ Wiki generated![/bold green]\n\n"
        f"[cyan]Site:[/cyan]   {site_path}\n"
        f"[cyan]Output:[/cyan] {output_dir}\n\n"
        f"[dim]Open in browser:[/dim] [bold]cortexcode wiki --open[/bold]\n"
        f"[dim]Or open directly:[/dim] {site_path}",
        border_style="green",
    ))

    if open_browser:
        import webbrowser
        webbrowser.open(site_path.as_uri())
