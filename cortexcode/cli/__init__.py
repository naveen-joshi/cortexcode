"""CLI command handlers."""

from cortexcode.cli.cli_ai_docs import handle_ai_docs_command
from cortexcode.cli.cli_complexity import handle_complexity_command
from cortexcode.cli.cli_context import handle_context_command
from cortexcode.cli.cli_dashboard import handle_dashboard_command
from cortexcode.cli.cli_dead_code import handle_dead_code_command
from cortexcode.cli.cli_diff import handle_diff_command
from cortexcode.cli.cli_diagrams import handle_diagrams_command
from cortexcode.cli.cli_docs import handle_docs_command
from cortexcode.cli.cli_explain import handle_explain_command
from cortexcode.cli.cli_find import handle_semantic_find_command
from cortexcode.cli.cli_impact import handle_impact_command
from cortexcode.cli.cli_index import handle_index_command
from cortexcode.cli.cli_report import handle_report_command
from cortexcode.cli.cli_scan import handle_scan_command
from cortexcode.cli.cli_search import handle_search_command
from cortexcode.cli.cli_servers import handle_lsp_command, handle_mcp_command
from cortexcode.cli.cli_stats import handle_stats_command
from cortexcode.cli.cli_support import require_ai_doc_generator, require_index_path
from cortexcode.cli.cli_watch import handle_watch_command
from cortexcode.cli.cli_wiki import handle_wiki_command
from cortexcode.cli.cli_workspace import (
    handle_workspace_add,
    handle_workspace_index,
    handle_workspace_init,
    handle_workspace_list,
    handle_workspace_remove,
    handle_workspace_search,
)
from cortexcode.cli.cli_config import handle_config_action

__all__ = [
    "handle_ai_docs_command",
    "handle_complexity_command",
    "handle_context_command",
    "handle_dashboard_command",
    "handle_dead_code_command",
    "handle_diff_command",
    "handle_diagrams_command",
    "handle_docs_command",
    "handle_explain_command",
    "handle_semantic_find_command",
    "handle_impact_command",
    "handle_index_command",
    "handle_report_command",
    "handle_scan_command",
    "handle_search_command",
    "handle_lsp_command",
    "handle_mcp_command",
    "handle_stats_command",
    "require_ai_doc_generator",
    "require_index_path",
    "handle_watch_command",
    "handle_wiki_command",
    "handle_workspace_add",
    "handle_workspace_index",
    "handle_workspace_init",
    "handle_workspace_list",
    "handle_workspace_remove",
    "handle_workspace_search",
    "handle_config_action",
]
