"""CLI - Command-line interface for CortexCode."""

import click
from pathlib import Path
from rich.console import Console

from cortexcode import indexer
from cortexcode.cli.cli_shell import SectionedHelpGroup, handle_completion_install, handle_completion_paths, handle_completion_show, install_legacy_alias_tips
from cortexcode.cli import handle_config_action
from cortexcode.cli import handle_ai_docs_command
from cortexcode.cli import handle_complexity_command
from cortexcode.cli import handle_context_command
from cortexcode.cli import handle_dashboard_command
from cortexcode.cli import handle_dead_code_command
from cortexcode.cli import handle_diff_command
from cortexcode.cli import handle_diagrams_command
from cortexcode.cli import handle_docs_command
from cortexcode.cli import handle_explain_command
from cortexcode.cli import handle_impact_command
from cortexcode.cli import handle_index_command
from cortexcode.cli import handle_report_command
from cortexcode.cli import handle_scan_command
from cortexcode.cli import handle_search_command
from cortexcode.cli import handle_lsp_command, handle_mcp_command
from cortexcode.cli import handle_stats_command
from cortexcode.cli import require_ai_doc_generator, require_index_path
from cortexcode.cli import handle_watch_command
from cortexcode.cli import handle_wiki_command
from cortexcode.cli import handle_workspace_add, handle_workspace_index, handle_workspace_init, handle_workspace_list, handle_workspace_remove, handle_workspace_search
from cortexcode.context import get_context, calculate_token_savings
from cortexcode.git_diff import get_diff_context
from cortexcode.docs import generate_all_docs
from cortexcode.terminal.analysis import (
    print_context as print_context_renderer,
    print_token_savings as print_token_savings_renderer,
)
from cortexcode.terminal.completion import (
    print_ai_docs_complete as print_ai_docs_complete_renderer,
    print_diagrams_complete as print_diagrams_complete_renderer,
    print_docs_complete as print_docs_complete_renderer,
)
from cortexcode.terminal.headers import (
    print_ai_docs_header as print_ai_docs_header_renderer,
    print_diagrams_header as print_diagrams_header_renderer,
    print_docs_header as print_docs_header_renderer,
    print_index_header as print_index_header_renderer,
)
from cortexcode.terminal.prompts import choose_report_type as choose_report_type_renderer
from cortexcode.terminal.reports import (
    get_available_reports as get_available_reports_renderer,
    print_project_profile_summary as print_project_profile_summary_renderer,
    print_terminal_report as print_terminal_report_renderer,
    show_index_summary as show_index_summary_renderer,
)
from cortexcode.terminal.stats import (
    print_query_savings as print_query_savings_renderer,
    print_stats_header as print_stats_header_renderer,
)
from cortexcode.watcher import start_watcher


console = Console()
DIAGRAM_TYPES = ["call_graph", "class", "sequence", "architecture", "imports", "dependencies", "entities", "file_tree"]
REPORT_TYPES = ["overview", "tech", "hotspots", "routes", "entities", "frontend", "cli"]


@click.group(cls=SectionedHelpGroup)
@click.version_option(version="0.6.0", prog_name="cortexcode")
def main():
    """AI-powered code indexing, analysis, and documentation."""
    pass


@main.group()
def analyze():
    """Search, inspect, trace, and analyze indexed code."""
    pass


@analyze.command("context")
@click.argument("query", required=False)
@click.option("-n", "--num-results", default=5, help="Number of results to return")
@click.option("-f", "--format", "output_format", default="text", type=click.Choice(["text", "json"]))
@click.option("--tokens", is_flag=True, help="Show token savings estimate")
def analyze_context(query, num_results, output_format, tokens):
    """Get relevant context for AI assistants."""
    handle_context_command(
        console,
        query,
        num_results,
        output_format,
        tokens,
        get_context,
        calculate_token_savings,
        require_index_path,
        print_context_renderer,
        print_token_savings_renderer,
    )


@analyze.command("search")
@click.argument("query")
@click.option("-t", "--type", "sym_type", default=None, help="Filter by type (function, class, method, interface)")
@click.option("-f", "--file", "file_filter", default=None, help="Filter by file path")
@click.option("-n", "--limit", default=20, help="Max results")
def analyze_search(query, sym_type, file_filter, limit):
    """Search indexed symbols (grep-like)."""
    _, index_path = require_index_path(console, ".")
    handle_search_command(console, query, sym_type, file_filter, limit, index_path)


@analyze.command("find")
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Max results")
def analyze_find(query, limit):
    """Semantic search — find symbols by meaning, not just name."""
    from cortexcode.semantic_search import semantic_search

    handle_semantic_find_command(
        console,
        query,
        limit,
        require_index_path,
        semantic_search,
    )


@analyze.command("diff")
@click.option("--ref", default="HEAD", help="Git ref to compare against (default: HEAD)")
@click.option("-f", "--format", "output_format", default="text", type=click.Choice(["text", "json"]))
def analyze_diff(ref, output_format):
    """Show changed symbols since last commit."""
    _, index_path = require_index_path(console, ".")
    handle_diff_command(console, ref, output_format, index_path, get_diff_context)


@analyze.command("stats")
def analyze_stats():
    """Show project index statistics and token savings."""
    handle_stats_command(
        console,
        require_index_path,
        print_stats_header_renderer,
        calculate_token_savings,
        print_token_savings_renderer,
        print_query_savings_renderer,
    )


@analyze.command("scan")
@click.argument("path", default=".", type=click.Path(exists=True))
def analyze_scan(path):
    """Scan dependencies and code for known issues and warnings."""
    from cortexcode.vuln_scan import scan_dependencies

    handle_scan_command(console, path, scan_dependencies)


@analyze.command("dead-code")
@click.argument("path", default=".", type=click.Path(exists=True))
def analyze_dead_code(path):
    """Detect potentially unused symbols (dead code)."""
    from cortexcode.analysis import detect_dead_code

    handle_dead_code_command(console, path, detect_dead_code)


@analyze.command("complexity")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--top", "-n", default=20, help="Show top N most complex functions")
@click.option("--min-score", default=0, help="Minimum complexity score to show")
def analyze_complexity(path, top, min_score):
    """Analyze code complexity metrics for all functions."""
    from cortexcode.analysis import compute_complexity

    handle_complexity_command(console, path, top, min_score, compute_complexity)


@analyze.command("impact")
@click.argument("symbol")
@click.argument("path", default=".", type=click.Path(exists=True))
def analyze_impact(symbol, path):
    """Analyze change impact for a symbol."""
    from cortexcode.analysis import analyze_change_impact

    handle_impact_command(console, symbol, path, analyze_change_impact)


@analyze.command("trace")
@click.argument("query")
@click.option("-p", "--path", default=".", help="Project path")
@click.option("-d", "--depth", default=5, help="Max trace depth")
@click.option("-c", "--context", default=5, help="Context lines to show")
def analyze_trace(query, path, depth, context):
    """Trace code flow from a symbol through the call graph."""
    from cortexcode.cli.cli_trace import handle_trace_command

    handle_trace_command(console, query, path, depth, context)


@analyze.command("flow")
@click.argument("query")
@click.option("-p", "--path", default=".", help="Project path")
@click.option("-d", "--depth", default=5, help="Max depth")
def analyze_flow(query, path, depth):
    """Analyze code flow for a concept and group by file."""
    from cortexcode.cli.cli_trace import handle_flow_command

    handle_flow_command(console, query, path, depth)


@analyze.command("explain")
@click.argument("symbol_name")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-p", "--provider", default=None, help="LLM provider")
@click.option("-m", "--model", default=None, help="Model name")
def analyze_explain(symbol_name, path, provider, model):
    """Explain a symbol using AI."""
    handle_explain_command(
        console,
        symbol_name,
        path,
        provider,
        model,
        require_ai_doc_generator,
        require_index_path,
    )


@main.group()
def generate():
    """Generate docs, diagrams, reports, and wiki."""
    pass


@generate.command("docs")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-o", "--output", default=".cortexcode/docs", help="Output directory")
@click.option("--open", "open_browser", is_flag=True, help="Open HTML docs in browser")
def generate_docs(path, output, open_browser):
    """Generate project documentation."""
    handle_docs_command(
        console,
        path,
        output,
        open_browser,
        require_index_path,
        print_docs_header_renderer,
        generate_all_docs,
        print_docs_complete_renderer,
    )


@generate.command("diagrams")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-o", "--output", default=".cortexcode/diagrams", help="Output directory")
@click.option("-t", "--type", "diagram_type", default=None, type=click.Choice(DIAGRAM_TYPES), help="Diagram type to generate")
@click.option("--viz", "visualize", is_flag=True, help="Open interactive visualization in browser")
def generate_diagrams(path, output, diagram_type, visualize):
    """Generate Mermaid diagrams or interactive visualization."""
    from cortexcode.docs.diagrams import save_diagrams
    from cortexcode.reports.site.viz import generate_viz_html

    if visualize:
        path, index_path = require_index_path(console, path)
        import json
        with open(index_path) as f:
            index_data = json.load(f)
        viz_path = Path(path) / ".cortexcode" / "graph.html"
        generate_viz_html(index_data, viz_path)
        console.print(f"[cyan]Opening visualization:[/cyan] {viz_path}")
        import webbrowser
        webbrowser.open(viz_path.as_uri())
        return

    handle_diagrams_command(
        console,
        path,
        output,
        diagram_type,
        require_index_path,
        print_diagrams_header_renderer,
        save_diagrams,
        DIAGRAM_TYPES,
        print_diagrams_complete_renderer,
    )


@generate.command("report")
@click.argument("report_type", required=False, type=click.Choice(REPORT_TYPES))
@click.argument("path", default=".", type=click.Path(exists=True))
def generate_report(report_type, path):
    """Show an interactive project report in the terminal."""
    handle_report_command(
        console,
        report_type,
        path,
        require_index_path,
        indexer.load_index,
        get_available_reports_renderer,
        REPORT_TYPES,
        choose_report_type_renderer,
        print_terminal_report_renderer,
    )


@generate.command("ai-docs")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-o", "--output", default=".cortexcode/ai-docs", help="Output directory")
@click.option("-p", "--provider", default=None, type=click.Choice(["openai", "anthropic", "google", "ollama"]), help="LLM provider")
@click.option("-m", "--model", default=None, help="Model name (e.g., gpt-4o, claude-sonnet-4-20250514)")
@click.option("--docs", multiple=True, default=["overview", "api", "architecture", "flows"], help="Which docs to generate")
def generate_ai_docs(path, output, provider, model, docs):
    """Generate AI-powered documentation using an LLM."""
    handle_ai_docs_command(
        console,
        path,
        output,
        provider,
        model,
        docs,
        require_ai_doc_generator,
        require_index_path,
        print_ai_docs_header_renderer,
        print_ai_docs_complete_renderer,
    )


@generate.command("wiki")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-o", "--output", default=".cortexcode/wiki", help="Output directory for wiki site")
@click.option("-p", "--provider", default=None, type=click.Choice(["openai", "anthropic", "google", "ollama"]), help="LLM provider")
@click.option("-m", "--model", default=None, help="Model name")
@click.option("--pages", multiple=True, help="Which pages to generate (default: all)")
@click.option("--no-modules", is_flag=True, help="Skip per-module page generation")
@click.option("--max-modules", default=15, help="Max number of module pages")
@click.option("--open", "open_browser", is_flag=True, help="Open wiki in browser after generation")
def generate_wiki(path, output, provider, model, pages, no_modules, max_modules, open_browser):
    """Generate a CodeWiki-style documentation site with AI."""
    handle_wiki_command(
        console, path, output, provider, model, pages or None,
        no_modules, max_modules, open_browser,
    )


@main.group()
def ai():
    """AI-powered code understanding and documentation commands."""
    pass


@ai.command("ask")
@click.argument("query")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-p", "--provider", default=None, type=click.Choice(["openai", "anthropic", "google", "ollama"]), help="LLM provider")
@click.option("-m", "--model", default=None, help="Model name")
def ai_ask(query, path, provider, model):
    """Ask a natural language question about the codebase."""
    ask.callback(query=query, path=path, provider=provider, model=model)


@ai.command("explain")
@click.argument("symbol_name")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-p", "--provider", default=None, help="LLM provider")
@click.option("-m", "--model", default=None, help="Model name")
def ai_explain(symbol_name, path, provider, model):
    """Explain a symbol using AI."""
    handle_explain_command(
        console,
        symbol_name,
        path,
        provider,
        model,
        require_ai_doc_generator,
        require_index_path,
    )


@ai.command("docs")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-o", "--output", default=".cortexcode/ai-docs", help="Output directory")
@click.option("-p", "--provider", default=None, type=click.Choice(["openai", "anthropic", "google", "ollama"]), help="LLM provider")
@click.option("-m", "--model", default=None, help="Model name (e.g., gpt-4o, claude-sonnet-4-20250514)")
@click.option("--docs", multiple=True, default=["overview", "api", "architecture", "flows"], help="Which docs to generate")
def ai_docs_group(path, output, provider, model, docs):
    """Generate AI-powered documentation using an LLM."""
    handle_ai_docs_command(
        console,
        path,
        output,
        provider,
        model,
        docs,
        require_ai_doc_generator,
        require_index_path,
        print_ai_docs_header_renderer,
        print_ai_docs_complete_renderer,
    )


@ai.command("wiki")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-o", "--output", default=".cortexcode/wiki", help="Output directory for wiki site")
@click.option("-p", "--provider", default=None, type=click.Choice(["openai", "anthropic", "google", "ollama"]), help="LLM provider")
@click.option("-m", "--model", default=None, help="Model name")
@click.option("--pages", multiple=True, help="Which pages to generate (default: all)")
@click.option("--no-modules", is_flag=True, help="Skip per-module page generation")
@click.option("--max-modules", default=15, help="Max number of module pages")
@click.option("--open", "open_browser", is_flag=True, help="Open wiki in browser after generation")
def ai_wiki(path, output, provider, model, pages, no_modules, max_modules, open_browser):
    """Generate a CodeWiki-style documentation site with AI."""
    handle_wiki_command(
        console, path, output, provider, model, pages or None,
        no_modules, max_modules, open_browser,
    )


@main.group()
def completion():
    """Shell completion helpers for cortexcode and cc."""
    pass


@completion.command("show")
@click.option("-s", "--shell", type=click.Choice(["powershell", "bash", "zsh", "fish"]), default=None, help="Shell type")
@click.option("-p", "--prog", type=click.Choice(["cortexcode", "cc", "both"]), default="both", help="Executable name")
def completion_show(shell, prog):
    """Print shell completion activation script."""
    programs = ["cortexcode", "cc"] if prog == "both" else [prog]
    for i, program in enumerate(programs):
        if i:
            console.print()
        handle_completion_show(console, shell, program)


@completion.command("install")
@click.option("-s", "--shell", type=click.Choice(["powershell", "bash", "zsh", "fish"]), default=None, help="Shell type")
@click.option("-p", "--prog", type=click.Choice(["cortexcode", "cc", "both"]), default="both", help="Executable name")
@click.option("--path", "target_path", default=None, help="Profile file to update")
def completion_install(shell, prog, target_path):
    """Install shell completion into your shell profile."""
    programs = ["cortexcode", "cc"] if prog == "both" else [prog]
    for program in programs:
        handle_completion_install(console, shell, program, target_path)


@completion.command("paths")
def completion_paths():
    """Show default shell profile paths used for completion installation."""
    handle_completion_paths(console)


@main.group()
def serve():
    """Run long-lived services and dashboards."""
    pass


@serve.command("watch")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-v", "--verbose", is_flag=True, help="Show file change events")
def serve_watch(path, verbose):
    """Watch for file changes and auto-reindex."""
    handle_watch_command(console, path, verbose, start_watcher)


@serve.command("dashboard")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--port", "-p", default=8787, help="Port to serve the dashboard")
def serve_dashboard(path, port):
    """Launch a live web dashboard with auto-refresh on index changes."""
    from cortexcode.dashboard import DashboardServer

    handle_dashboard_command(console, path, port, indexer, DashboardServer)


@serve.command("lsp")
def serve_lsp():
    """Start Language Server Protocol server (stdin/stdout)."""
    from cortexcode.lsp_server import run_lsp_server

    handle_lsp_command(run_lsp_server)


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-o", "--output", default=".cortexcode/index.json", help="Output file path")
@click.option("-v", "--verbose", is_flag=True, help="Show verbose output")
@click.option("-w", "--watch", is_flag=True, help="Start watching after indexing")
@click.option("-i", "--incremental", is_flag=True, help="Only re-index changed files")
@click.option("-t", "--include-tests/--no-index-tests", default=None, help="Include test files (default: from config or exclude)")
@click.option("-e", "--exclude", multiple=True, help="Patterns to exclude (can repeat)")
@click.option("-I", "--include", multiple=True, help="Patterns to include, e.g., 'apps/*', 'packages/*'")
@click.option("-r", "--root", default=None, help="Monorepo root (for nx-style projects)")
@click.option("-n", "--dry-run", is_flag=True, help="Preview what would be indexed without indexing")
def index(path, output, verbose, watch, incremental, include_tests, exclude, include, root, dry_run):
    """Index a directory and save the code graph."""
    handle_index_command(
        console,
        path,
        output,
        verbose,
        watch,
        incremental,
        include_tests,
        exclude,
        include,
        root,
        dry_run,
        indexer,
        print_index_header_renderer,
        print_project_profile_summary_renderer,
        show_index_summary_renderer,
        start_watcher,
    )


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-v", "--verbose", is_flag=True, help="Show file change events")
def watch(path, verbose):
    """Watch for file changes and auto-reindex."""
    handle_watch_command(console, path, verbose, start_watcher)


@main.command()
@click.argument("query", required=False)
@click.option("-n", "--num-results", default=5, help="Number of results to return")
@click.option("-f", "--format", "output_format", default="text", type=click.Choice(["text", "json"]))
@click.option("--tokens", is_flag=True, help="Show token savings estimate")
def context(query, num_results, output_format, tokens):
    """Get relevant context for AI assistants."""
    handle_context_command(
        console,
        query,
        num_results,
        output_format,
        tokens,
        get_context,
        calculate_token_savings,
        require_index_path,
        print_context_renderer,
        print_token_savings_renderer,
    )


@main.command()
@click.argument("query")
@click.option("-t", "--type", "sym_type", default=None, help="Filter by type (function, class, method, interface)")
@click.option("-f", "--file", "file_filter", default=None, help="Filter by file path")
@click.option("-n", "--limit", default=20, help="Max results")
def search(query, sym_type, file_filter, limit):
    """Search indexed symbols (grep-like)."""
    _, index_path = require_index_path(console, ".")
    handle_search_command(console, query, sym_type, file_filter, limit, index_path)


@main.command()
@click.option("--ref", default="HEAD", help="Git ref to compare against (default: HEAD)")
@click.option("-f", "--format", "output_format", default="text", type=click.Choice(["text", "json"]))
def diff(ref, output_format):
    """Show changed symbols since last commit (git diff-aware context)."""
    _, index_path = require_index_path(console, ".")
    handle_diff_command(console, ref, output_format, index_path, get_diff_context)


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-o", "--output", default=".cortexcode/docs", help="Output directory")
@click.option("--open", "open_browser", is_flag=True, help="Open HTML docs in browser")
def docs(path, output, open_browser):
    """Generate project documentation."""
    handle_docs_command(
        console,
        path,
        output,
        open_browser,
        require_index_path,
        print_docs_header_renderer,
        generate_all_docs,
        print_docs_complete_renderer,
    )


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-o", "--output", default=".cortexcode/diagrams", help="Output directory")
@click.option("-t", "--type", "diagram_type", default=None, type=click.Choice(DIAGRAM_TYPES), help="Diagram type to generate")
@click.option("--viz", "visualize", is_flag=True, help="Open interactive visualization in browser")
def diagrams(path, output, diagram_type, visualize):
    """Generate Mermaid diagrams from index (no LLM required)."""
    from cortexcode.docs.diagrams import save_diagrams
    from cortexcode.reports.site.viz import generate_viz_html

    if visualize:
        path, index_path = require_index_path(console, path)
        import json
        with open(index_path) as f:
            index_data = json.load(f)
        viz_path = Path(path) / ".cortexcode" / "graph.html"
        generate_viz_html(index_data, viz_path)
        console.print(f"[cyan]Opening visualization:[/cyan] {viz_path}")
        import webbrowser
        webbrowser.open(viz_path.as_uri())
        return

    handle_diagrams_command(
        console,
        path,
        output,
        diagram_type,
        require_index_path,
        print_diagrams_header_renderer,
        save_diagrams,
        DIAGRAM_TYPES,
        print_diagrams_complete_renderer,
    )


@main.command()
@click.argument("report_type", required=False, type=click.Choice(REPORT_TYPES))
@click.argument("path", default=".", type=click.Path(exists=True))
def report(report_type, path):
    """Show an interactive project report in the terminal."""
    handle_report_command(
        console,
        report_type,
        path,
        require_index_path,
        indexer.load_index,
        get_available_reports_renderer,
        REPORT_TYPES,
        choose_report_type_renderer,
        print_terminal_report_renderer,
    )


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-o", "--output", default=".cortexcode/ai-docs", help="Output directory")
@click.option("-p", "--provider", default=None, type=click.Choice(["openai", "anthropic", "google", "ollama"]), help="LLM provider")
@click.option("-m", "--model", default=None, help="Model name (e.g., gpt-4o, claude-sonnet-4-20250514)")
@click.option("--docs", multiple=True, default=["overview", "api", "architecture", "flows"], help="Which docs to generate")
def ai_docs(path, output, provider, model, docs):
    """Generate AI-powered documentation using LLM."""
    handle_ai_docs_command(
        console,
        path,
        output,
        provider,
        model,
        docs,
        require_ai_doc_generator,
        require_index_path,
        print_ai_docs_header_renderer,
        print_ai_docs_complete_renderer,
    )


@main.command()
@click.argument("symbol_name")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-p", "--provider", default=None, help="LLM provider")
@click.option("-m", "--model", default=None, help="Model name")
def explain(symbol_name, path, provider, model):
    """Explain a symbol using AI."""
    handle_explain_command(
        console,
        symbol_name,
        path,
        provider,
        model,
        require_ai_doc_generator,
        require_index_path,
    )


@main.command()
@click.argument("query")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-p", "--provider", default=None, type=click.Choice(["openai", "anthropic", "google", "ollama"]), help="LLM provider")
@click.option("-m", "--model", default=None, help="Model name")
def ask(query, path, provider, model):
    """Ask a natural language question about the codebase."""
    from pathlib import Path as P
    from cortexcode.knowledge.build import build_knowledge_pack
    from cortexcode.ai_docs.config import get_config
    from cortexcode.ai_docs.explainer import Explainer
    from cortexcode.cli.cli_wiki import _ensure_api_key

    project_path = P(path).resolve()
    index_path = project_path / ".cortexcode" / "index.json"
    if not index_path.exists():
        console.print("[bold red]Error:[/bold red] No index found. Run [cyan]cortexcode index[/cyan] first.")
        return

    resolved_provider = provider or get_config().provider
    api_key = _ensure_api_key(console, resolved_provider)
    if not api_key:
        console.print("[bold red]Cannot answer without an API key.[/bold red]")
        return

    console.print(f"[dim]Building knowledge pack...[/dim]")
    pack = build_knowledge_pack(index_path)
    console.print(f"[dim]{pack.symbol_count} symbols, {len(pack.concepts)} concepts loaded[/dim]\n")

    explainer = Explainer(provider=resolved_provider, model=model, api_key=api_key)
    answer, usage = explainer.explain(query, pack)

    console.print(answer)

    if usage:
        console.print(f"\n[dim]({usage.total_tokens:,} tokens · {usage.provider}/{usage.model})[/dim]")


@main.command()
@click.argument("action", type=click.Choice(["set", "get", "list", "status"]))
@click.argument("key", required=False)
@click.argument("value", required=False)
def config(action, key, value):
    """Manage CortexCode configuration."""
    handle_config_action(console, action, key, value)


@main.command()
def stats():
    """Show project index statistics and token savings."""
    handle_stats_command(
        console,
        require_index_path,
        print_stats_header_renderer,
        calculate_token_savings,
        print_token_savings_renderer,
        print_query_savings_renderer,
    )


@main.group()
def mcp():
    """MCP server management."""
    pass


@mcp.command()
def start():
    """Start MCP server for AI agent integration (stdin/stdout)."""
    from cortexcode.mcp import run_stdio_server
    handle_mcp_command(console, run_stdio_server)


@mcp.command()
def setup():
    """Configure MCP for IDEs (auto-detect and setup)."""
    from cortexcode.cli.cli_servers import handle_mcp_setup
    handle_mcp_setup(console)


@main.command()
def lsp():
    """Start Language Server Protocol server (stdin/stdout)."""
    from cortexcode.lsp_server import run_lsp_server

    handle_lsp_command(run_lsp_server)


@main.group()
def bundle():
    """Bundle management - export/import pre-indexed code graphs."""
    pass


@bundle.command()
@click.argument("path", default=".")
@click.option("-o", "--output", default=None, help="Output path for bundle")
@click.option("-n", "--name", default=None, help="Bundle name")
def export(path, output, name):
    """Export index as a shareable bundle (.ccb file)."""
    from cortexcode.cli.cli_bundle import handle_bundle_export
    handle_bundle_export(console, path, output or ".", name)


@bundle.command()
@click.argument("bundle_path")
@click.option("-o", "--output", default=None, help="Output directory for index")
def import_cmd(bundle_path, output):
    """Import a bundle into the project."""
    from cortexcode.cli.cli_bundle import handle_bundle_import
    handle_bundle_import(console, bundle_path, output)


@bundle.command()
@click.argument("bundle_path")
def info(bundle_path):
    """Show bundle information without importing."""
    from cortexcode.cli.cli_bundle import handle_bundle_info
    handle_bundle_info(console, bundle_path)


@main.group()
def package():
    """Index external packages."""
    pass


@package.command()
@click.argument("package_name")
@click.option("-l", "--language", default="python", type=click.Choice(["python", "javascript", "typescript"]), help="Package language")
@click.option("-o", "--output", default=None, help="Output directory")
def index(package_name, language, output):
    """Index an external package (e.g., cortexcode package index requests)."""
    from cortexcode.cli.cli_package import handle_package_index
    handle_package_index(console, package_name, language, output)


@package.command()
def list():
    """List available packages."""
    from cortexcode.cli.cli_package import handle_package_list
    handle_package_list(console)


@main.group()
def jobs():
    """Background job management."""
    pass


@jobs.command()
@click.option("-s", "--status", type=click.Choice(["running", "completed", "failed"]), help="Filter by status")
def list(status):
    """List background jobs."""
    from cortexcode.cli.cli_jobs import handle_jobs_list
    handle_jobs_list(console, status)


@jobs.command()
@click.option("-a", "--all", is_flag=True, help="Clear all jobs including running")
def clear(all):
    """Clear completed jobs."""
    from cortexcode.cli.cli_jobs import handle_jobs_clear
    handle_jobs_clear(console, all)


@jobs.command()
@click.argument("job_id")
def watch(job_id):
    """Watch a job's progress."""
    from cortexcode.cli.cli_jobs import handle_jobs_watch
    handle_jobs_watch(console, job_id)


@main.group()
def githook():
    """Git hook integration for auto-indexing."""
    pass


@githook.command()
@click.option("-t", "--type", "hook_type", default="post-commit", help="Hook type")
def install(hook_type):
    """Install git hook for auto-indexing."""
    from cortexcode.cli.cli_githook import handle_githook_install
    handle_githook_install(console, hook_type)


@githook.command()
@click.option("-t", "--type", "hook_type", default="post-commit", help="Hook type")
def uninstall(hook_type):
    """Remove git hook."""
    from cortexcode.cli.cli_githook import handle_githook_uninstall
    handle_githook_uninstall(console, hook_type)


@githook.command()
def precommit():
    """Install pre-commit hook for security scanning."""
    from cortexcode.cli.cli_githook import handle_githook_precommit
    handle_githook_precommit(console)


@main.command()
@click.argument("query")
@click.option("-p", "--path", default=".", help="Project path")
@click.option("-d", "--depth", default=5, help="Max trace depth")
@click.option("-c", "--context", default=5, help="Context lines to show")
def trace(query, path, depth, context):
    """Trace code flow from a symbol through call graph.

    Examples:
        cortexcode trace login
        cortexcode trace auth -d 10
    """
    from cortexcode.cli.cli_trace import handle_trace_command
    handle_trace_command(console, query, path, depth, context)


@main.command()
@click.argument("query")
@click.option("-p", "--path", default=".", help="Project path")
@click.option("-d", "--depth", default=5, help="Max depth")
def flow(query, path, depth):
    """Analyze code flow for a concept and group by file.

    Examples:
        cortexcode flow auth
        cortexcode flow payment
    """
    from cortexcode.cli.cli_trace import handle_flow_command
    handle_flow_command(console, query, path, depth)


@main.command(name="find", hidden=True)
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Max results")
def semantic_find(query, limit):
    """Semantic search — find symbols by meaning, not just name.

    Examples: cortexcode find "authentication handler"
              cortexcode find "database models"
              cortexcode find "user login flow"
    """
    from cortexcode.semantic_search import semantic_search

    handle_semantic_find_command(
        console,
        query,
        limit,
        require_index_path,
        semantic_search,
    )


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def scan(path):
    """Scan dependencies for known issues and security warnings."""
    from cortexcode.vuln_scan import scan_dependencies

    handle_scan_command(console, path, scan_dependencies)


@main.command(hidden=True)
@click.argument("path", default=".", type=click.Path(exists=True))
def dead_code(path):
    """Detect potentially unused symbols (dead code)."""
    from cortexcode.analysis import detect_dead_code

    handle_dead_code_command(console, path, detect_dead_code)


@main.command(hidden=True)
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--top", "-n", default=20, help="Show top N most complex functions")
@click.option("--min-score", default=0, help="Minimum complexity score to show")
def complexity(path, top, min_score):
    """Analyze code complexity metrics for all functions."""
    from cortexcode.analysis import compute_complexity

    handle_complexity_command(console, path, top, min_score, compute_complexity)


@main.command(hidden=True)
@click.argument("symbol")
@click.argument("path", default=".", type=click.Path(exists=True))
def impact(symbol, path):
    """Analyze change impact — what breaks if a symbol is modified."""
    from cortexcode.analysis import analyze_change_impact

    handle_impact_command(console, symbol, path, analyze_change_impact)


@main.group()
def workspace():
    """Multi-repo workspace management."""
    pass


@workspace.command("init")
@click.argument("path", default=".", type=click.Path(exists=True))
def workspace_init(path):
    """Initialize a workspace at the given path."""
    from cortexcode.workspace import Workspace

    handle_workspace_init(console, path, Workspace)


@workspace.command("add")
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("--alias", "-a", default=None, help="Short alias for the repo")
def workspace_add(repo_path, alias):
    """Add a repo to the workspace."""
    from cortexcode.workspace import Workspace

    handle_workspace_add(console, repo_path, alias, Workspace)


@workspace.command("remove")
@click.argument("alias_or_path")
def workspace_remove(alias_or_path):
    """Remove a repo from the workspace."""
    from cortexcode.workspace import Workspace

    handle_workspace_remove(console, alias_or_path, Workspace)


@workspace.command("list")
def workspace_list():
    """List all repos in the workspace."""
    from cortexcode.workspace import Workspace

    handle_workspace_list(console, Workspace)


@workspace.command("index")
@click.option("--full", is_flag=True, help="Full re-index (not incremental)")
def workspace_index(full):
    """Index all repos in the workspace."""
    from cortexcode.workspace import Workspace

    handle_workspace_index(console, full, Workspace)


@workspace.command("search")
@click.argument("query")
def workspace_search(query):
    """Search symbols across all workspace repos."""
    from cortexcode.workspace import Workspace

    handle_workspace_search(console, query, Workspace)


@main.command(hidden=True)
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--port", "-p", default=8787, help="Port to serve the dashboard")
def dashboard(path, port):
    """Launch a live web dashboard with auto-refresh on index changes."""
    from cortexcode.dashboard import DashboardServer

    handle_dashboard_command(console, path, port, indexer, DashboardServer)


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("-o", "--output", default=".cortexcode/wiki", help="Output directory for wiki site")
@click.option("-p", "--provider", default=None, type=click.Choice(["openai", "anthropic", "google", "ollama"]), help="LLM provider")
@click.option("-m", "--model", default=None, help="Model name")
@click.option("--pages", multiple=True, help="Which pages to generate (default: all)")
@click.option("--no-modules", is_flag=True, help="Skip per-module page generation")
@click.option("--max-modules", default=15, help="Max number of module pages")
@click.option("--open", "open_browser", is_flag=True, help="Open wiki in browser after generation")
def wiki(path, output, provider, model, pages, no_modules, max_modules, open_browser):
    """Generate a CodeWiki-style documentation site with AI.

    Builds a multi-page interactive wiki from the project index using
    Gemini (default) or other LLM providers. Includes concept search
    for non-technical queries like 'how does authentication work?'
    """
    handle_wiki_command(
        console, path, output, provider, model, pages or None,
        no_modules, max_modules, open_browser,
    )


@main.command()
@click.argument("query")
@click.option("-p", "--path", default=".", help="Project path")
@click.option("-d", "--depth", default=5, help="Max trace depth")
@click.option("-c", "--context", default=5, help="Context lines to show")
def trace(query, path, depth, context):
    """Trace code flow from a symbol through call graph.

    Examples:
        cortexcode trace login
        cortexcode trace auth -d 10
    """
    from cortexcode.cli.cli_trace import handle_trace_command
    handle_trace_command(console, query, path, depth, context)


@main.command()
@click.argument("query")
@click.option("-p", "--path", default=".", help="Project path")
@click.option("-d", "--depth", default=5, help="Max depth")
def flow(query, path, depth):
    """Analyze code flow for a concept and group by file.

    Examples:
        cortexcode flow auth
        cortexcode flow payment
    """
    from cortexcode.cli.cli_trace import handle_flow_command
    handle_flow_command(console, query, path, depth)


@main.command(name="find", hidden=True)
@click.argument("query")
@click.option("-n", "--limit", default=10, help="Max results")
def semantic_find(query, limit):
    """Semantic search — find symbols by meaning, not just name.

    Examples: cortexcode find "authentication handler"
              cortexcode find "database models"
              cortexcode find "user login flow"
    """
    from cortexcode.semantic_search import semantic_search

    handle_semantic_find_command(
        console,
        query,
        limit,
        require_index_path,
        semantic_search,
    )


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def scan(path):
    """Scan dependencies for known issues and security warnings."""
    from cortexcode.vuln_scan import scan_dependencies

    handle_scan_command(console, path, scan_dependencies)


@main.command(hidden=True)
@click.argument("path", default=".", type=click.Path(exists=True))
def dead_code(path):
    """Detect potentially unused symbols (dead code)."""
    from cortexcode.analysis import detect_dead_code

    handle_dead_code_command(console, path, detect_dead_code)


@main.command(hidden=True)
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--top", "-n", default=20, help="Show top N most complex functions")
@click.option("--min-score", default=0, help="Minimum complexity score to show")
def complexity(path, top, min_score):
    """Analyze code complexity metrics for all functions."""
    from cortexcode.analysis import compute_complexity

    handle_complexity_command(console, path, top, min_score, compute_complexity)


@main.command(hidden=True)
@click.argument("symbol")
@click.argument("path", default=".", type=click.Path(exists=True))
def impact(symbol, path):
    """Analyze change impact — what breaks if a symbol is modified."""
    from cortexcode.analysis import analyze_change_impact

    handle_impact_command(console, symbol, path, analyze_change_impact)


main.command_sections = {
    "Core": ["index", "config", "workspace"],
    "Explore & Analyze": ["analyze", "ai", "bundle", "package", "jobs"],
    "Generate": ["generate"],
    "Integrate & Automate": ["serve", "mcp", "githook", "completion"],
}


install_legacy_alias_tips(
    main,
    console=console,
    aliases={
        "ask": "ai ask",
        "ai-docs": "ai docs",
        "explain": "ai explain",
        "wiki": "ai wiki",
        "watch": "serve watch",
        "dashboard": "serve dashboard",
        "lsp": "serve lsp",
        "context": "analyze context",
        "search": "analyze search",
        "diff": "analyze diff",
        "stats": "analyze stats",
        "scan": "analyze scan",
        "trace": "analyze trace",
        "flow": "analyze flow",
        "find": "analyze find",
        "dead-code": "analyze dead-code",
        "complexity": "analyze complexity",
        "impact": "analyze impact",
        "docs": "generate docs",
        "diagrams": "generate diagrams",
        "report": "generate report",
    },
)


if __name__ == "__main__":
    main()
