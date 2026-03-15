import json
import time
import sys
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeRemainingColumn
from rich.table import Table


def _load_questionary():
    try:
        import questionary
    except ImportError:
        return None
    return questionary


def _load_user_config() -> dict:
    config_path = Path.home() / ".cortexcode" / "config.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_user_config(config: dict) -> None:
    config_path = Path.home() / ".cortexcode" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def _load_post_index_preferences() -> dict:
    config = _load_user_config()
    prefs = config.get("post_index_wizard", {})
    if isinstance(prefs, dict):
        return prefs
    return {}


def _save_post_index_preferences(preferences: dict) -> None:
    config = _load_user_config()
    config["post_index_wizard"] = preferences
    _save_user_config(config)


def _should_show_post_index_wizard(watch: bool, disabled: bool, force: bool) -> bool:
    if force:
        return True
    preferences = _load_post_index_preferences()
    return not disabled and preferences.get("enabled", True) and not watch and sys.stdin.isatty() and sys.stdout.isatty()


def _prompt_generate_now() -> bool:
    questionary = _load_questionary()
    if questionary:
        answer = questionary.confirm("Generate docs, diagrams, reports, or setup now?", default=False).ask()
        return bool(answer)
    return click.confirm("Generate docs, diagrams, reports, or setup now?", default=False)


def _get_recommended_targets(index_data: dict, preferences: dict) -> list[str]:
    saved_targets = preferences.get("targets")
    if isinstance(saved_targets, list) and saved_targets:
        return saved_targets

    recommended = ["docs", "diagrams", "report"]
    profile = index_data.get("project_profile", {}) if isinstance(index_data, dict) else {}
    route_count = profile.get("route_count", 0)
    entity_count = profile.get("entity_count", 0)
    files = index_data.get("files", {}) if isinstance(index_data, dict) else {}
    symbol_count = sum(
        len(file_data.get("symbols", [])) if isinstance(file_data, dict) else len(file_data)
        for file_data in files.values()
    )

    if route_count or entity_count:
        recommended.append("dashboard")
    if 0 < symbol_count <= 500:
        recommended.append("viz")

    seen = []
    for item in recommended:
        if item not in seen:
            seen.append(item)
    return seen


def _prompt_generation_targets(console: Console, defaults: list[str] | None = None, recommended: list[str] | None = None) -> list[str]:
    core_options = [
        ("docs", "Project docs"),
        ("diagrams", "Mermaid diagrams"),
        ("report", "Interactive terminal report"),
        ("viz", "Interactive graph visualization"),
        ("dashboard", "Live dashboard"),
    ]
    ai_options = [
        ("ai_docs", "AI docs"),
        ("wiki", "CodeWiki"),
    ]
    setup_options = [
        ("mcp_setup", "Configure MCP for your editor"),
    ]
    options = core_options + ai_options + setup_options
    defaults = defaults or []
    recommended = recommended or []
    questionary = _load_questionary()
    if questionary:
        choices = [questionary.Separator("══ Core outputs ══")]
        choices.extend(
            questionary.Choice(
                title=f"{label}{' [recommended]' if value in recommended else ''}",
                value=value,
                checked=value in defaults,
            )
            for value, label in core_options
        )
        choices.append(questionary.Separator("══ AI-powered ══"))
        choices.extend(
            questionary.Choice(
                title=f"{label}{' [recommended]' if value in recommended else ''}",
                value=value,
                checked=value in defaults,
            )
            for value, label in ai_options
        )
        choices.append(questionary.Separator("══ Setup ══"))
        choices.extend(
            questionary.Choice(
                title=f"{label}{' [recommended]' if value in recommended else ''}",
                value=value,
                checked=value in defaults,
            )
            for value, label in setup_options
        )
        selections = questionary.checkbox(
            "Select what to generate",
            choices=choices,
            validate=lambda items: True if items else "Select at least one option.",
        ).ask()
        return selections or []

    console.print("\n[bold]Select what to generate:[/bold]")
    for idx, (_, label) in enumerate(options, 1):
        suffix = " [recommended]" if options[idx - 1][0] in recommended else ""
        console.print(f"  {idx}. {label}{suffix}")
    default_indexes = [str(idx) for idx, (value, _) in enumerate(options, 1) if value in defaults]
    raw_value = click.prompt(
        "Enter choices as comma-separated numbers",
        default=",".join(default_indexes) if default_indexes else "1,2",
        show_default=True,
    )
    selected = []
    for part in raw_value.split(","):
        part = part.strip()
        if not part.isdigit():
            continue
        index = int(part) - 1
        if 0 <= index < len(options):
            selected.append(options[index][0])
    seen = []
    for item in selected:
        if item not in seen:
            seen.append(item)
    return seen


def _prompt_provider(default: str | None = None) -> str:
    from cortexcode.ai_docs.config import get_config

    provider = default or get_config().provider or "google"
    choices = ["google", "openai", "anthropic", "ollama"]
    questionary = _load_questionary()
    if questionary:
        answer = questionary.select("Choose provider", choices=choices, default=provider).ask()
        return answer or provider
    return click.prompt("Choose provider", type=click.Choice(choices), default=provider, show_choices=True)


def _ensure_provider_access(console: Console, provider: str) -> bool:
    from cortexcode.ai_docs.config import AIConfig, get_api_key, get_config, set_api_key, set_config

    config = get_config()
    set_config(AIConfig(provider=provider, model=config.model, temperature=config.temperature, max_tokens=config.max_tokens))

    if provider == "ollama":
        return True

    if get_api_key(provider):
        return True

    provider_labels = {
        "google": ("Gemini", "https://aistudio.google.com/apikey"),
        "openai": ("OpenAI", "https://platform.openai.com/api-keys"),
        "anthropic": ("Anthropic", "https://console.anthropic.com/settings/keys"),
    }
    label, url = provider_labels.get(provider, (provider, ""))
    console.print(
        f"\n[yellow]No API key found for {label}.[/yellow]\n"
        f"[dim]Get your key at:[/dim] [cyan]{url}[/cyan]\n"
    )

    questionary = _load_questionary()
    if questionary:
        api_key = questionary.password(f"Enter your {label} API key (leave blank to skip)").ask() or ""
    else:
        api_key = click.prompt(
            f"Enter your {label} API key (leave blank to skip)",
            default="",
            show_default=False,
            hide_input=True,
        ).strip()

    if not api_key:
        console.print(f"[dim]Skipped. You can set it later with:[/dim] [cyan]cortexcode config set {provider}_api_key YOUR_KEY[/cyan]\n")
        return False

    set_api_key(provider, api_key)
    console.print(f"[green]✓[/green] API key saved for {label}.\n")
    return True


def _prompt_report_type(available_reports: list[str], default: str | None = None) -> str:
    questionary = _load_questionary()
    selected_default = default if default in available_reports else (available_reports[0] if available_reports else "overview")
    if questionary:
        answer = questionary.select("Choose report type", choices=available_reports, default=selected_default).ask()
        return answer or selected_default
    return click.prompt(
        "Choose report type",
        type=click.Choice(available_reports),
        default=selected_default,
        show_choices=True,
    )


def _prompt_dashboard_port(default: int) -> int:
    questionary = _load_questionary()
    if questionary:
        answer = questionary.text("Dashboard port", default=str(default), validate=lambda value: value.isdigit() or "Enter a valid port").ask()
        return int(answer or default)
    return int(click.prompt("Dashboard port", default=default, type=int, show_default=True))


def _prompt_diagram_types(defaults: list[str]) -> list[str]:
    diagram_types = ["call_graph", "class", "sequence", "architecture", "imports", "dependencies", "entities", "file_tree"]
    questionary = _load_questionary()
    if questionary:
        selections = questionary.checkbox(
            "Choose diagram types",
            choices=[questionary.Choice(title=item, value=item, checked=item in defaults) for item in diagram_types],
            validate=lambda items: True if items else "Select at least one diagram type.",
        ).ask()
        return selections or defaults

    raw_value = click.prompt(
        "Choose diagram types (comma-separated)",
        default=",".join(defaults),
        show_default=True,
    )
    values = [item.strip() for item in raw_value.split(",") if item.strip() in diagram_types]
    return values or defaults


def _prompt_ai_doc_types(defaults: list[str]) -> list[str]:
    doc_types = ["overview", "api", "architecture", "flows"]
    questionary = _load_questionary()
    if questionary:
        selections = questionary.checkbox(
            "Choose AI doc types",
            choices=[questionary.Choice(title=item, value=item, checked=item in defaults) for item in doc_types],
            validate=lambda items: True if items else "Select at least one AI doc type.",
        ).ask()
        return selections or defaults

    raw_value = click.prompt(
        "Choose AI doc types (comma-separated)",
        default=",".join(defaults),
        show_default=True,
    )
    values = [item.strip() for item in raw_value.split(",") if item.strip() in doc_types]
    return values or defaults


def _prompt_confirm(message: str, default: bool) -> bool:
    questionary = _load_questionary()
    if questionary:
        answer = questionary.confirm(message, default=default).ask()
        return bool(answer)
    return click.confirm(message, default=default)


def _prompt_max_modules(default: int) -> int:
    questionary = _load_questionary()
    if questionary:
        answer = questionary.text("Max module pages", default=str(default), validate=lambda value: value.isdigit() or "Enter a valid number").ask()
        return int(answer or default)
    return int(click.prompt("Max module pages", default=default, type=int, show_default=True))


def _prompt_save_preferences() -> bool:
    questionary = _load_questionary()
    if questionary:
        answer = questionary.confirm("Save these choices as defaults for future index runs?", default=True).ask()
        return bool(answer)
    return click.confirm("Save these choices as defaults for future index runs?", default=True)


def _prompt_show_wizard_next_time(default: bool) -> bool:
    questionary = _load_questionary()
    if questionary:
        answer = questionary.confirm("Show this wizard automatically after future index runs?", default=default).ask()
        return bool(answer)
    return click.confirm("Show this wizard automatically after future index runs?", default=default)


def _run_post_index_wizard(console: Console, path: Path, index_data: dict) -> None:
    import webbrowser

    from cortexcode import indexer
    from cortexcode.cli import handle_ai_docs_command, handle_dashboard_command, handle_diagrams_command, handle_docs_command, handle_wiki_command
    from cortexcode.cli.cli_servers import handle_mcp_setup
    from cortexcode.cli.cli_support import require_ai_doc_generator, require_index_path
    from cortexcode.docs import generate_all_docs
    from cortexcode.docs.diagrams import save_diagrams
    from cortexcode.dashboard import DashboardServer
    from cortexcode.reports.site.viz import generate_viz_html
    from cortexcode.terminal.completion import print_ai_docs_complete, print_diagrams_complete, print_docs_complete
    from cortexcode.terminal.headers import print_ai_docs_header, print_diagrams_header, print_docs_header
    from cortexcode.terminal.reports import get_available_reports, print_terminal_report

    preferences = _load_post_index_preferences()
    if not _prompt_generate_now():
        return

    recommended_targets = _get_recommended_targets(index_data, preferences)
    default_targets = preferences.get("targets") or recommended_targets
    targets = _prompt_generation_targets(console, default_targets, recommended_targets)
    if not targets:
        return

    provider = preferences.get("provider")
    if any(target in {"ai_docs", "wiki"} for target in targets):
        provider = _prompt_provider(provider)
        if not _ensure_provider_access(console, provider):
            targets = [target for target in targets if target not in {"ai_docs", "wiki"}]
            if not targets:
                return

    report_type = preferences.get("report_type")
    if "report" in targets:
        available_reports = get_available_reports(index_data, ["overview", "tech", "hotspots", "routes", "entities", "frontend", "cli"])
        report_type = _prompt_report_type(available_reports, report_type)

    dashboard_port = int(preferences.get("dashboard_port", 8787))
    if "dashboard" in targets:
        dashboard_port = _prompt_dashboard_port(dashboard_port)

    docs_open_browser = bool(preferences.get("open_docs_browser", False))
    if "docs" in targets:
        docs_open_browser = _prompt_confirm("Open generated docs in browser?", docs_open_browser)

    recommended_diagrams = index_data.get("project_profile", {}).get("recommendations", {}).get("diagrams", [])
    diagram_defaults = preferences.get("diagram_types") or [item for item in recommended_diagrams if item in ["call_graph", "class", "sequence", "architecture", "imports", "dependencies", "entities", "file_tree"]] or ["architecture", "call_graph"]
    selected_diagram_types = diagram_defaults
    if "diagrams" in targets:
        selected_diagram_types = _prompt_diagram_types(diagram_defaults)

    ai_doc_defaults = preferences.get("ai_doc_types") or ["overview", "api", "architecture", "flows"]
    selected_ai_doc_types = ai_doc_defaults
    if "ai_docs" in targets:
        selected_ai_doc_types = _prompt_ai_doc_types(ai_doc_defaults)

    wiki_open_browser = bool(preferences.get("open_wiki_browser", False))
    wiki_include_modules = bool(preferences.get("wiki_include_modules", True))
    wiki_max_modules = int(preferences.get("wiki_max_modules", 15))
    if "wiki" in targets:
        wiki_open_browser = _prompt_confirm("Open generated CodeWiki in browser?", wiki_open_browser)
        wiki_include_modules = _prompt_confirm("Include per-module wiki pages?", wiki_include_modules)
        if wiki_include_modules:
            wiki_max_modules = _prompt_max_modules(wiki_max_modules)

    viz_open_browser = bool(preferences.get("open_viz_browser", True))
    if "viz" in targets:
        viz_open_browser = _prompt_confirm("Open graph visualization in browser?", viz_open_browser)

    wizard_enabled = _prompt_show_wizard_next_time(bool(preferences.get("enabled", True)))

    if _prompt_save_preferences():
        _save_post_index_preferences(
            {
                "targets": targets,
                "provider": provider,
                "report_type": report_type,
                "dashboard_port": dashboard_port,
                "diagram_types": selected_diagram_types,
                "ai_doc_types": selected_ai_doc_types,
                "open_docs_browser": docs_open_browser,
                "open_wiki_browser": wiki_open_browser,
                "wiki_include_modules": wiki_include_modules,
                "wiki_max_modules": wiki_max_modules,
                "open_viz_browser": viz_open_browser,
                "enabled": wizard_enabled,
            }
        )

    if "docs" in targets:
        handle_docs_command(
            console,
            path,
            path / ".cortexcode" / "docs",
            docs_open_browser,
            require_index_path,
            print_docs_header,
            generate_all_docs,
            print_docs_complete,
        )

    if "diagrams" in targets:
        output_dir = path / ".cortexcode" / "diagrams"
        diagram_types = ["call_graph", "class", "sequence", "architecture", "imports", "dependencies", "entities", "file_tree"]
        if len(selected_diagram_types) == 1:
            handle_diagrams_command(
                console,
                path,
                output_dir,
                selected_diagram_types[0],
                require_index_path,
                print_diagrams_header,
                save_diagrams,
                diagram_types,
                print_diagrams_complete,
            )
        elif len(selected_diagram_types) == len(diagram_types):
            handle_diagrams_command(
                console,
                path,
                output_dir,
                None,
                require_index_path,
                print_diagrams_header,
                save_diagrams,
                diagram_types,
                print_diagrams_complete,
            )
        else:
            _, index_path = require_index_path(console, path)
            print_diagrams_header(console, path)
            for diagram_type in selected_diagram_types:
                save_diagrams(index_path, output_dir, diagram_type=diagram_type)
            generated_files = ["DIAGRAMS.md", *[f"{item}.mmd" for item in selected_diagram_types]]
            print_diagrams_complete(console, output_dir, generated_files)

    if "ai_docs" in targets:
        handle_ai_docs_command(
            console,
            path,
            path / ".cortexcode" / "ai-docs",
            provider,
            None,
            tuple(selected_ai_doc_types),
            require_ai_doc_generator,
            require_index_path,
            print_ai_docs_header,
            print_ai_docs_complete,
        )

    if "wiki" in targets:
        handle_wiki_command(
            console,
            path,
            path / ".cortexcode" / "wiki",
            provider,
            None,
            None,
            not wiki_include_modules,
            wiki_max_modules,
            wiki_open_browser,
        )

    if "report" in targets:
        print_terminal_report(console, report_type or "overview", index_data, path)

    if "viz" in targets:
        viz_path = path / ".cortexcode" / "graph.html"
        generate_viz_html(index_data, viz_path)
        if viz_open_browser:
            console.print(f"[cyan]Opening visualization:[/cyan] {viz_path}")
            webbrowser.open(viz_path.as_uri())
        else:
            console.print(f"[green]✓[/green] Visualization generated: {viz_path}")

    if "mcp_setup" in targets:
        handle_mcp_setup(console)

    if "dashboard" in targets:
        handle_dashboard_command(console, path, dashboard_port, indexer, DashboardServer)


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
    no_post_index_wizard: bool,
    force_wizard: bool,
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

    if _should_show_post_index_wizard(watch, no_post_index_wizard, force_wizard):
        _run_post_index_wizard(console, path, index_data)

    if watch:
        console.print("\n[yellow]Starting watcher...[/yellow]")
        console.print("[dim]Press Ctrl+C to stop[/dim]")
        start_watcher(path, verbose=verbose)
