"""CLI - Command-line interface for CortexCode."""

import click
from rich.console import Console

from cortexcode import indexer
from cortexcode.cli_config import handle_config_action
from cortexcode.cli_ai_docs import handle_ai_docs_command
from cortexcode.cli_complexity import handle_complexity_command
from cortexcode.cli_context import handle_context_command
from cortexcode.cli_dashboard import handle_dashboard_command
from cortexcode.cli_dead_code import handle_dead_code_command
from cortexcode.cli_diff import handle_diff_command
from cortexcode.cli_diagrams import handle_diagrams_command
from cortexcode.cli_docs import handle_docs_command
from cortexcode.cli_explain import handle_explain_command
from cortexcode.cli_find import handle_semantic_find_command
from cortexcode.cli_impact import handle_impact_command
from cortexcode.cli_index import handle_index_command
from cortexcode.cli_report import handle_report_command
from cortexcode.cli_scan import handle_scan_command
from cortexcode.cli_search import handle_search_command
from cortexcode.cli_servers import handle_lsp_command, handle_mcp_command
from cortexcode.cli_stats import handle_stats_command
from cortexcode.cli_support import require_ai_doc_generator, require_index_path
from cortexcode.cli_watch import handle_watch_command
from cortexcode.cli_workspace import handle_workspace_add, handle_workspace_index, handle_workspace_init, handle_workspace_list, handle_workspace_remove, handle_workspace_search
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
def diagrams(path, output, diagram_type):
    """Generate Mermaid diagrams from index (no LLM required)."""
    from cortexcode.docs.diagrams import save_diagrams

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


@main.command()
def mcp():
    """Start MCP server for AI agent integration (stdin/stdout)."""
    from cortexcode.mcp_server import run_stdio_server

    handle_mcp_command(console, run_stdio_server)


@main.command()
def lsp():
    """Start Language Server Protocol server (stdin/stdout)."""
    from cortexcode.lsp_server import run_lsp_server

    handle_lsp_command(run_lsp_server)


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


@main.command("dead-code")
@click.argument("path", default=".", type=click.Path(exists=True))
def dead_code(path):
    """Detect potentially unused symbols (dead code)."""
    from cortexcode.analysis import detect_dead_code

    handle_dead_code_command(console, path, detect_dead_code)


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--top", "-n", default=20, help="Show top N most complex functions")
@click.option("--min-score", default=0, help="Minimum complexity score to show")
def complexity(path, top, min_score):
    """Analyze code complexity metrics for all functions."""
    from cortexcode.analysis import compute_complexity

    handle_complexity_command(console, path, top, min_score, compute_complexity)


@main.command()
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


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--port", "-p", default=8787, help="Port to serve the dashboard")
def dashboard(path, port):
    """Launch a live web dashboard with auto-refresh on index changes."""
    from cortexcode.dashboard import DashboardServer

    handle_dashboard_command(console, path, port, indexer, DashboardServer)


if __name__ == "__main__":
    main()
