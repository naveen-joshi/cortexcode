"""Prompt templates for AI documentation generation."""

from typing import Dict, List, Any


SYSTEM_PROMPT = """You are an expert software architect and technical writer. Your task is to generate high-quality documentation for a codebase based on its structure and symbol information.

Generate clear, concise, and informative documentation that:
1. Explains what each component does
2. Shows how components relate to each other
3. Provides usage examples where appropriate
4. Uses proper markdown formatting

Focus on accuracy and helpfulness. If information is unclear, make reasonable assumptions but note them."""


def generate_project_overview_prompt(index_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate prompt for project overview documentation."""
    
    files = index_data.get("files", {})
    call_graph = index_data.get("call_graph", {})
    
    # Summarize key files
    file_summary = []
    for path, data in list(files.items())[:20]:
        symbols = data.get("symbols", []) if isinstance(data, dict) else data
        symbol_count = len(symbols)
        file_summary.append(f"- `{path}` ({symbol_count} symbols)")
    
    # Summarize call graph
    entry_points = list(call_graph.keys())[:10]
    
    prompt = f"""Generate a comprehensive project overview for this codebase.

## Project Info
- Root: {index_data.get('project_root', 'Unknown')}
- Total Files: {len(files)}
- Total Symbols: {len(call_graph)}

## Key Files
{chr(10).join(file_summary)}

## Entry Points / Main Functions
{chr(10).join(f"- {ep}" for ep in entry_points)}

Please provide:
1. A brief description of what this project does
2. The main components and their purposes
3. How the application is structured
4. Key entry points and how to use them

Write in markdown format with clear sections."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]


def generate_module_docs_prompt(module_name: str, module_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate prompt for module-level documentation."""
    
    symbols = module_data.get("symbols", [])
    imports = module_data.get("imports", [])
    exports = module_data.get("exports", [])
    
    symbol_details = []
    for sym in symbols[:15]:
        sym_type = sym.get("type", "unknown")
        name = sym.get("name", "unknown")
        params = sym.get("params", [])
        doc = sym.get("doc", "")
        
        if sym_type == "function" or sym_type == "method":
            params_str = ", ".join(params) if params else "none"
            symbol_details.append(f"- `{name}({params_str})` - {doc or 'No description'}")
        elif sym_type == "class":
            methods = [m.get("name", "") for m in sym.get("methods", [])]
            if not methods:
                methods = [
                    s.get("name", "")
                    for s in symbols
                    if s.get("type") == "method" and (s.get("parent") == name or s.get("class") == name)
                ]
            symbol_details.append(f"- class `{name}` - {doc or 'No description'}")
            if methods:
                symbol_details.append(f"  - Methods: {', '.join(methods[:5])}")
        else:
            symbol_details.append(f"- {sym_type} `{name}` - {doc or 'No description'}")
    
    prompt = f"""Generate detailed documentation for the module `{module_name}`.

## Module: {module_name}

### Imports
{chr(10).join(f"- {imp}" for imp in imports[:10]) if imports else "No imports found"}

### Exports
{chr(10).join(f"- {exp}" for exp in exports[:10]) if exports else "No explicit exports"}

### Symbols
{chr(10).join(symbol_details)}

Please provide:
1. What this module does
2. How to use the main components
3. Any important patterns or conventions used

Write in markdown format."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]


def generate_api_docs_prompt(index_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate API documentation prompt."""
    
    files = index_data.get("files", {})
    
    # Collect all public APIs
    apis = []
    for path, data in files.items():
        symbols = data.get("symbols", []) if isinstance(data, dict) else data
        for sym in symbols:
            sym_type = sym.get("type", "unknown")
            if sym_type in ["function", "class", "method"]:
                name = sym.get("name", "unknown")
                params = sym.get("params", [])
                doc = sym.get("doc", "")
                ret_type = sym.get("return_type", "")
                
                sig = f"{name}({', '.join(params)})" if params else name
                if ret_type:
                    sig += f" -> {ret_type}"
                
                apis.append(f"- `{sig}` in `{path}` - {doc or 'No description'}")
    
    prompt = f"""Generate API documentation for this codebase.

## Available APIs
{chr(10).join(apis[:50])}

Please organize these into logical groups and provide:
1. A description of each API
2. Parameters and return types
3. Usage examples where helpful

Write in markdown format with clear sections."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]


def generate_architecture_prompt(index_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate architecture documentation with diagrams."""
    
    files = index_data.get("files", {})
    call_graph = index_data.get("call_graph", {})
    imports = index_data.get("imports", {})
    
    # Group files by directory
    directories: Dict[str, List[str]] = {}
    for path in files.keys():
        parts = path.split("/")
        if len(parts) > 1:
            dir_name = parts[0]
            if dir_name not in directories:
                directories[dir_name] = []
            directories[dir_name].append(path)
    
    # Build dependency info
    deps = []
    for source, targets in list(imports.items())[:20]:
        deps.append(f"- `{source}` imports: {', '.join(targets[:5])}")
    
    prompt = f"""Generate architecture documentation for this codebase.

## Directory Structure
{chr(10).join(f"- `{dir}/` ({len(files)} files)" for dir, files in sorted(directories.items()))}

## Key Dependencies
{chr(10).join(deps)}

## Call Graph (Top functions)
{chr(10).join(f"- {caller} -> {', '.join(callees[:3])}" for caller, callees in list(call_graph.items())[:15])}

Please provide:
1. High-level architecture description
2. Component relationships (use Mermaid diagrams if helpful)
3. Data flow patterns
4. Key design decisions

Write in markdown format with Mermaid diagrams for visualizations."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]


def generate_flow_docs_prompt(index_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate code flow documentation."""
    
    call_graph = index_data.get("call_graph", {})
    files = index_data.get("files", {})
    
    # Find main flows
    flows = []
    for caller, callees in list(call_graph.items())[:20]:
        if callees:
            flow = f"- `{caller}` calls: {', '.join(callees[:5])}"
            flows.append(flow)
    
    prompt = f"""Generate code flow documentation showing how execution flows through this codebase.

## Function Calls
{chr(10).join(flows)}

Please provide:
1. Main execution paths
2. Important function sequences
3. Entry points and their downstream effects

Use Mermaid sequence diagrams where helpful. Write in markdown format."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]


def explain_symbol_prompt(symbol_name: str, symbol_data: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate prompt to explain a specific symbol."""
    
    sym_type = symbol_data.get("type", "unknown")
    params = symbol_data.get("params", [])
    doc = symbol_data.get("doc", "")
    file_path = symbol_data.get("file", "unknown")
    
    # Get callers and callees
    call_graph = context.get("call_graph", {})
    callers = call_graph.get(symbol_name, [])
    all_callers = [k for k, v in call_graph.items() if symbol_name in v]
    
    prompt = f"""Explain the symbol `{symbol_name}` in detail.

## Symbol Info
- Type: {sym_type}
- File: {file_path}
- Parameters: {', '.join(params) if params else 'None'}
- Documentation: {doc or 'No documentation'}

## Context
- Called by: {', '.join(all_callers[:5]) if all_callers else 'None'}
- Calls: {', '.join(callers[:5]) if callers else 'None'}

Please provide:
1. What this symbol does
2. How it's used
3. Important considerations for developers

Write in clear, concise markdown."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
