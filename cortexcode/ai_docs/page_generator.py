"""Page-oriented documentation generators using the knowledge pack."""

from __future__ import annotations

from typing import Any

from cortexcode.knowledge.models import ConceptEntry, KnowledgePack, Snippet


def _format_snippet_block(snippet: Snippet) -> str:
    """Format a snippet as a fenced code block with citation."""
    lang = snippet.language or ""
    header = f"**`{snippet.file_path}`** (lines {snippet.start_line}–{snippet.end_line})"
    if snippet.symbol_name:
        header += f" — `{snippet.symbol_name}`"
    return f"{header}\n```{lang}\n{snippet.content}\n```"


def _format_symbol_summary(sym: dict[str, Any]) -> str:
    """Format a symbol as a one-line summary."""
    name = sym.get("name", "?")
    stype = sym.get("type", "symbol")
    params = sym.get("params", [])
    sig = f"{name}({', '.join(params)})" if params else name
    doc = sym.get("doc", "")
    line = f"- **`{sig}`** ({stype})"
    if doc:
        line += f" — {doc[:120]}"
    if sym.get("file"):
        line += f"  \n  _defined in `{sym['file']}`_"
    return line


# ---------------------------------------------------------------------------
# Prompt builders — each returns (system_message, user_message)
# ---------------------------------------------------------------------------

def build_overview_prompt(pack: KnowledgePack) -> tuple[str, str]:
    """Build the prompt for PROJECT_OVERVIEW.md."""
    top_files = sorted(
        pack.file_summaries.items(),
        key=lambda x: -x[1].get("symbol_count", 0),
    )[:20]
    file_lines = [f"- `{fp}` ({fs['symbol_count']} symbols)" for fp, fs in top_files]

    fw_lines = [f"- {fw.get('name', '?')} ({fw.get('type', '')})" for fw in pack.frameworks[:10]]

    ep_lines = []
    for ep in pack.entry_points[:10]:
        ep_lines.append(f"- `{ep.get('name', '?')}` in `{ep.get('file', '?')}`")

    system = (
        "You are an expert technical writer. Generate a comprehensive, readable "
        "project overview in Markdown. Write for someone who has never seen this "
        "codebase. Explain what the project does, its main components, how they "
        "connect, and how to get started. Include illustrative code snippets "
        "where helpful. Use clear headings and short paragraphs."
    )
    user = f"""Generate a comprehensive project overview for **{pack.project_name}**.

## Project Facts
- Languages: {', '.join(pack.languages)}
- Files: {pack.file_count}
- Symbols: {pack.symbol_count}
- Call edges: {pack.call_edge_count}

## Key Files
{chr(10).join(file_lines)}

## Frameworks Detected
{chr(10).join(fw_lines) if fw_lines else 'None detected'}

## Entry Points
{chr(10).join(ep_lines) if ep_lines else 'Not identified'}

Write a readable overview with these sections:
1. What this project does (in plain language)
2. Main components and their purposes
3. How the application is structured
4. Key entry points and how to use them
5. Getting started tips"""

    return system, user


def build_architecture_prompt(pack: KnowledgePack) -> tuple[str, str]:
    """Build the prompt for ARCHITECTURE.md."""
    # Group files by top-level directory
    dirs: dict[str, int] = {}
    for fp in pack.file_summaries:
        parts = fp.split("/")
        d = parts[0] if len(parts) > 1 else "."
        dirs[d] = dirs.get(d, 0) + 1
    dir_lines = [f"- `{d}/` ({c} files)" for d, c in sorted(dirs.items(), key=lambda x: -x[1])[:15]]

    dep_lines = []
    for src, targets in list(pack.file_dependencies.items())[:20]:
        dep_lines.append(f"- `{src}` → {', '.join(f'`{t}`' for t in targets[:4])}")

    system = (
        "You are a senior software architect. Generate architecture documentation "
        "in Markdown with Mermaid diagrams. Explain the structure clearly for both "
        "technical and non-technical readers. Start with a high-level overview, "
        "then drill into component relationships."
    )
    user = f"""Generate architecture documentation for **{pack.project_name}**.

## Directory Structure
{chr(10).join(dir_lines)}

## File Dependencies (sample)
{chr(10).join(dep_lines) if dep_lines else 'None tracked'}

## Languages: {', '.join(pack.languages)}
## Total files: {pack.file_count}, symbols: {pack.symbol_count}

Please provide:
1. High-level architecture description (what are the main layers/components?)
2. Component relationship diagram (use Mermaid)
3. Data flow patterns
4. Key design decisions and patterns used
5. A brief explanation for non-technical readers"""

    return system, user


def build_module_prompt(
    pack: KnowledgePack,
    module_path: str,
    file_data: dict[str, Any],
) -> tuple[str, str]:
    """Build the prompt for MODULES/<module>.md."""
    symbols = file_data.get("symbols", [])
    imports = file_data.get("imports", [])
    exports = file_data.get("exports", [])

    sym_lines = [_format_symbol_summary(s) for s in symbols[:20]]
    import_lines = [f"- `{i.get('module', '?')}`" for i in imports[:10]]
    export_lines = [f"- `{e.get('name', '?')}`" for e in exports[:10]]

    # Include snippets if available
    snippet_blocks = []
    for snip in pack.snippets.get(module_path, [])[:3]:
        snippet_blocks.append(_format_snippet_block(snip))

    system = (
        "You are an expert technical writer. Generate clear module documentation "
        "in Markdown. Explain what this module does, how its components work, and "
        "provide usage examples. Write for someone new to the codebase."
    )
    user = f"""Generate documentation for the module `{module_path}`.

## Symbols
{chr(10).join(sym_lines) if sym_lines else 'No symbols found'}

## Imports
{chr(10).join(import_lines) if import_lines else 'None'}

## Exports
{chr(10).join(export_lines) if export_lines else 'None'}

## Code Snippets
{chr(10).join(snippet_blocks) if snippet_blocks else 'No snippets available'}

Please provide:
1. What this module does (plain language)
2. Key classes/functions and their purposes
3. How to use the main components
4. Important patterns or conventions"""

    return system, user


def build_flows_prompt(pack: KnowledgePack) -> tuple[str, str]:
    """Build the prompt for FLOWS.md."""
    flow_lines = []
    for caller, callees in list(pack.call_graph.items())[:25]:
        if callees:
            flow_lines.append(f"- `{caller}` → {', '.join(f'`{c}`' for c in callees[:5])}")

    ep_flows = []
    for ep in pack.entry_points[:5]:
        name = ep.get("name", "?")
        cg = pack.call_graph.get(name, [])
        if cg:
            ep_flows.append(f"- Entry `{name}` → {', '.join(f'`{c}`' for c in cg[:6])}")

    system = (
        "You are an expert technical writer. Generate code flow documentation "
        "showing how execution moves through the codebase. Use Mermaid sequence "
        "diagrams. Explain flows in plain language a non-technical reader can follow."
    )
    user = f"""Generate code flow documentation for **{pack.project_name}**.

## Call Graph (sample)
{chr(10).join(flow_lines) if flow_lines else 'No call graph data'}

## Entry Point Flows
{chr(10).join(ep_flows) if ep_flows else 'No entry points identified'}

Please provide:
1. Main execution paths (explained in plain language)
2. Sequence diagrams for important flows (Mermaid)
3. Entry points and their downstream effects
4. How data moves through the system"""

    return system, user


def build_api_reference_prompt(pack: KnowledgePack) -> tuple[str, str]:
    """Build the prompt for API_REFERENCE.md."""
    route_lines = []
    for r in pack.api_routes[:30]:
        method = r.get("method", "?")
        path = r.get("path", "?")
        fp = r.get("file", "?")
        route_lines.append(f"- **{method}** `{path}` — defined in `{fp}`")

    # Collect public functions
    pub_syms = []
    for name, sym in list(pack.symbol_index.items())[:40]:
        if sym.get("type") in ("function", "class", "method"):
            pub_syms.append(_format_symbol_summary(sym))

    system = (
        "You are an expert API documentation writer. Generate clear API reference "
        "documentation in Markdown. Group endpoints and functions logically. "
        "Include request/response examples where possible."
    )
    user = f"""Generate API reference documentation for **{pack.project_name}**.

## API Routes
{chr(10).join(route_lines) if route_lines else 'No API routes detected'}

## Public Functions/Classes (sample)
{chr(10).join(pub_syms[:30]) if pub_syms else 'None'}

Please provide:
1. API endpoints grouped by resource/feature
2. Function/class reference grouped by module
3. Parameters and return types
4. Usage examples where helpful"""

    return system, user


def build_concepts_prompt(pack: KnowledgePack) -> tuple[str, str]:
    """Build the prompt for CONCEPTS.md — plain-language explanations for non-technical users."""
    concept_blocks = []
    for concept in pack.concepts[:15]:
        lines = [f"### {concept.name.replace('_', ' ').title()}"]
        lines.append(f"Related code: {', '.join(f'`{s}`' for s in concept.related_symbols[:6])}")
        lines.append(f"Related files: {', '.join(f'`{f}`' for f in concept.related_files[:4])}")
        if concept.related_flows:
            for flow in concept.related_flows[:2]:
                lines.append(f"Flow: {' → '.join(f'`{f}`' for f in flow)}")
        if concept.snippets:
            lines.append("")
            lines.append(_format_snippet_block(concept.snippets[0]))
        concept_blocks.append("\n".join(lines))

    system = (
        "You are an expert technical writer who specializes in making complex "
        "software systems understandable to non-technical people. Generate a "
        "concepts guide that explains the major features and mechanisms of this "
        "codebase in plain language. Use analogies and everyday language. "
        "Include code snippets only as illustrations, not as the primary content. "
        "For each concept, explain WHAT it does, WHY it matters, and HOW it works "
        "at a high level."
    )
    user = f"""Generate a concepts guide for **{pack.project_name}**.

This guide is for non-technical users who want to understand how the system works.

## Detected Concepts

{chr(10).join(concept_blocks) if concept_blocks else 'No specific concepts detected — generate a general overview.'}

For each concept, please write:
1. A simple explanation of what it is (no jargon)
2. Why it matters in this application
3. How it works at a high level (step by step, in plain language)
4. Which parts of the code are involved (with brief code snippet illustrations)

If a concept wasn't detected but seems important based on the code, add it.

Write in a friendly, approachable tone. Avoid technical jargon where possible, and explain any technical terms you must use."""

    return system, user


def build_getting_started_prompt(pack: KnowledgePack) -> tuple[str, str]:
    """Build the prompt for GETTING_STARTED.md."""
    system = (
        "You are an expert developer advocate. Generate a getting started guide "
        "that helps new developers set up and explore this project. Be practical "
        "and action-oriented."
    )
    ep_lines = [f"- `{ep.get('name', '?')}` in `{ep.get('file', '?')}`" for ep in pack.entry_points[:5]]
    fw_lines = [f"- {fw.get('name', '?')}" for fw in pack.frameworks[:5]]

    user = f"""Generate a Getting Started guide for **{pack.project_name}**.

## Project Facts
- Languages: {', '.join(pack.languages)}
- Files: {pack.file_count}
- Frameworks: {', '.join(fw_lines) if fw_lines else 'None detected'}

## Entry Points
{chr(10).join(ep_lines) if ep_lines else 'Not identified'}

Please provide:
1. Prerequisites and setup steps
2. How to run the project
3. Key files to look at first
4. Common development tasks
5. Where to find documentation"""

    return system, user


# ---------------------------------------------------------------------------
# Registry of all page generators
# ---------------------------------------------------------------------------

PAGE_GENERATORS: dict[str, dict[str, Any]] = {
    "overview": {
        "title": "Project Overview",
        "output_file": "PROJECT_OVERVIEW.md",
        "prompt_builder": build_overview_prompt,
    },
    "architecture": {
        "title": "Architecture",
        "output_file": "ARCHITECTURE.md",
        "prompt_builder": build_architecture_prompt,
    },
    "flows": {
        "title": "Code Flows",
        "output_file": "FLOWS.md",
        "prompt_builder": build_flows_prompt,
    },
    "api": {
        "title": "API Reference",
        "output_file": "API_REFERENCE.md",
        "prompt_builder": build_api_reference_prompt,
    },
    "concepts": {
        "title": "Concepts Guide",
        "output_file": "CONCEPTS.md",
        "prompt_builder": build_concepts_prompt,
    },
    "getting_started": {
        "title": "Getting Started",
        "output_file": "GETTING_STARTED.md",
        "prompt_builder": build_getting_started_prompt,
    },
}
