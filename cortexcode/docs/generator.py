"""Main documentation generator - orchestrates all doc generation."""

import json
from pathlib import Path
from collections import defaultdict

from cortexcode.docs.templates import CSS_TEMPLATE, TYPE_COLORS, LANG_COLORS, D3_CDN_URL
from cortexcode.docs.javascript import JS_TEMPLATE
from cortexcode.docs.html_generators import (
    generate_tree_html,
    generate_symbols_html,
    generate_imports_html,
    generate_exports_html,
    generate_routes_html,
    generate_entities_html,
)

D3_LOCAL_FILE = "d3.min.js"


def _ensure_d3_local(output_dir: Path) -> str:
    """Ensure D3.js is available locally. Returns the script src to use."""
    local_path = output_dir / D3_LOCAL_FILE
    if local_path.exists() and local_path.stat().st_size > 100_000:
        return D3_LOCAL_FILE
    
    try:
        import urllib.request
        urllib.request.urlretrieve(D3_CDN_URL, str(local_path))
        if local_path.exists() and local_path.stat().st_size > 100_000:
            return D3_LOCAL_FILE
    except Exception:
        pass
    
    return D3_CDN_URL


def generate_all_docs(index_path: Path, output_dir: Path) -> None:
    """Generate all documentation files from the index."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    index = json.loads(index_path.read_text(encoding="utf-8"))
    
    d3_src = _ensure_d3_local(output_dir)
    
    generate_readme(index, output_dir / "README.md")
    generate_api_docs(index, output_dir / "API.md")
    generate_structure_docs(index, output_dir / "STRUCTURE.md")
    generate_flow_docs(index, output_dir / "FLOWS.md")
    generate_html_docs(index, output_dir / "index.html", d3_src=d3_src)


def generate_readme(index: dict, output_path: Path) -> None:
    """Generate project README."""
    files = index.get("files", {})
    call_graph = index.get("call_graph", {})
    
    directories = defaultdict(list)
    for rel_path in files.keys():
        parts = Path(rel_path).parts
        if len(parts) > 1:
            directories[parts[0]].append(rel_path)
    
    lines = [
        "# Project Documentation",
        "",
        "## Overview",
        "",
        f"**Project Root:** `{index.get('project_root', 'N/A')}`",
        f"**Last Indexed:** {index.get('last_indexed', 'N/A')}",
        "",
        "## Key Modules",
        "",
    ]
    
    for dir_name, dir_files in sorted(directories.items()):
        lines.append(f"- `{dir_name}/` — {len(dir_files)} files")
    
    lines.extend([
        "",
        "## Entry Points",
        "",
    ])
    
    for rel_path in files.keys():
        if Path(rel_path).name in ("main.py", "app.py", "server.py", "cli.py", "__main__.py"):
            lines.append(f"- `{rel_path}`")
    
    if not any(Path(p).name in ("main.py", "app.py", "server.py", "cli.py", "__main__.py") for p in files.keys()):
        lines.append("  (No obvious entry points found)")
    
    lines.extend([
        "",
        "## Symbol Count",
        "",
        f"- **Files:** {len(files)}",
        f"- **Symbols:** {len(call_graph)}",
    ])
    
    output_path.write_text("\n".join(lines), encoding="utf-8")


def generate_api_docs(index: dict, output_path: Path) -> None:
    """Generate API documentation."""
    files = index.get("files", {})
    
    lines = [
        "# API Documentation",
        "",
    ]
    
    for rel_path, file_data in sorted(files.items()):
        symbols = file_data.get("symbols", []) if isinstance(file_data, dict) else file_data
        if not symbols:
            continue
        
        lines.append(f"## {rel_path}")
        lines.append("")
        
        for sym in symbols:
            name = sym.get("name", "unknown")
            sym_type = sym.get("type", "function")
            params = sym.get("params", [])
            doc = sym.get("doc", "")
            
            if sym_type == "class":
                lines.append(f"### class `{name}`")
            else:
                params_str = ", ".join(params) if params else ""
                lines.append(f"### `{name}({params_str})`")
            
            lines.append("")
            if doc:
                lines.append(f"> {doc}")
                lines.append("")
            
            if sym.get("methods"):
                lines.append("**Methods:**")
                for method in sym.get("methods", []):
                    method_params = ", ".join(method.get("params", []))
                    lines.append(f"- `{method.get('name', '')}({method_params})`")
                lines.append("")
    
    output_path.write_text("\n".join(lines), encoding="utf-8")


def generate_structure_docs(index: dict, output_path: Path) -> None:
    """Generate project structure documentation."""
    files = index.get("files", {})
    
    lines = [
        "# Project Structure",
        "",
        "```",
    ]
    
    for rel_path in sorted(files.keys()):
        lines.append(rel_path)
    
    lines.append("```")
    
    output_path.write_text("\n".join(lines), encoding="utf-8")


def generate_flow_docs(index: dict, output_path: Path) -> None:
    """Generate call flow documentation."""
    call_graph = index.get("call_graph", {})
    
    lines = [
        "# Call Flows",
        "",
        "## Call Graph",
        "",
    ]
    
    for symbol, calls in sorted(call_graph.items()):
        if calls:
            lines.append(f"### {symbol}")
            lines.append("")
            for call in calls:
                lines.append(f"  → {call}")
            lines.append("")
    
    if not any(call_graph.values()):
        lines.append("*No call relationships found.*")
    
    output_path.write_text("\n".join(lines), encoding="utf-8")


def generate_html_docs(index: dict, output_path: Path, d3_src: str = D3_CDN_URL) -> None:
    """Generate interactive HTML documentation."""
    files = index.get("files", {})
    call_graph = index.get("call_graph", {})
    file_deps = index.get("file_dependencies", {})
    project_root = index.get("project_root", "")
    last_indexed = index.get("last_indexed", "")
    
    all_symbols = []
    file_tree = {}
    framework_counts = {
        "react": 0, "react-native": 0, "expo": 0,
        "angular": 0, "nextjs": 0, "nestjs": 0, "express": 0,
        "flutter": 0, "compose": 0, "android": 0,
        "swiftui": 0, "uikit": 0, "ios": 0,
        "spring": 0, "fastapi": 0, "django": 0, "flask": 0, "aspnet": 0,
    }
    language_counts = {}
    type_counts = {}
    all_imports = []
    all_exports = []
    all_api_routes = []
    all_entities = []
    files_with_most_symbols = []
    
    for rel_path, file_data in files.items():
        symbols = file_data.get("symbols", []) if isinstance(file_data, dict) else file_data
        imports = file_data.get("imports", []) if isinstance(file_data, dict) else []
        exports = file_data.get("exports", []) if isinstance(file_data, dict) else []
        api_routes = file_data.get("api_routes", []) if isinstance(file_data, dict) else []
        entities = file_data.get("entities", []) if isinstance(file_data, dict) else []
        
        ext = Path(rel_path).suffix
        language_counts[ext] = language_counts.get(ext, 0) + 1
        
        parts = rel_path.replace("\\", "/").split("/")
        current = file_tree
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        if parts[-1] not in current:
            current[parts[-1]] = symbols
        
        all_imports.extend([{"file": rel_path, **imp} for imp in imports])
        all_exports.extend([{"file": rel_path, **exp} for exp in exports])
        all_api_routes.extend([{"file": rel_path, **route} for route in api_routes])
        all_entities.extend([{"file": rel_path, **ent} for ent in entities])
        
        files_with_most_symbols.append({"file": rel_path, "count": len(symbols)})
        
        for sym in symbols:
            sym["file"] = rel_path
            all_symbols.append(sym)
            t = sym.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
            
            fw = sym.get("framework")
            if fw:
                for key in framework_counts:
                    if key in fw:
                        framework_counts[key] += 1
                        break
    
    files_with_most_symbols.sort(key=lambda x: x["count"], reverse=True)
    
    non_empty_calls = sum(1 for v in call_graph.values() if v)
    total_call_edges = sum(len(v) for v in call_graph.values() if v)
    top_callers = sorted(
        [(k, len(v)) for k, v in call_graph.items() if v],
        key=lambda x: x[1], reverse=True
    )[:10]
    
    project_name = Path(project_root).name
    
    # Pre-build HTML fragments
    fw_cards_html = ""
    if any(framework_counts.values()):
        fw_items = "".join(
            f'<div style="background:var(--bg);padding:12px 20px;border-radius:var(--radius-sm);text-align:center;">'
            f'<div style="font-size:24px;font-weight:700;color:var(--accent);">{c}</div>'
            f'<div style="font-size:12px;color:var(--text3);margin-top:2px;">{fw}</div></div>'
            for fw, c in framework_counts.items() if c > 0
        )
        fw_cards_html = (
            '<div class="card"><div class="card-title">Detected Frameworks</div>'
            '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px;">'
            f'{fw_items}</div></div>'
        )
    
    filter_tabs_html = "".join(
        f'<div class="filter-tab" onclick="filterByType(\'{t}\', this)">{t.title()} ({c})</div>'
        for t, c in sorted(type_counts.items(), key=lambda x: -x[1])
    )
    
    top_files_rows = "".join(
        f'<tr><td style="color:var(--text2);font-size:12px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{f["file"]}">{f["file"]}</td>'
        f'<td style="font-weight:600;color:var(--accent);">{f["count"]}</td>'
        f'<td><div class="bar" style="width:{min(100, f["count"] * 100 // max(1, files_with_most_symbols[0]["count"] if files_with_most_symbols else 1))}%;"></div></td></tr>'
        for f in files_with_most_symbols[:8]
    )
    
    top_callers_rows = "".join(
        f'<tr><td style="color:var(--accent);font-size:13px;cursor:pointer;" onclick="highlightGraphNode(\'{name}\')">{name}</td>'
        f'<td style="font-weight:600;">{count}</td>'
        f'<td><div class="bar" style="width:{min(100, count * 100 // max(1, top_callers[0][1] if top_callers else 1))}%;background:var(--accent2);"></div></td></tr>'
        for name, count in top_callers[:8]
    )
    
    # JSON data for JavaScript
    search_data_json = json.dumps([
        {"name": s.get("name",""), "type": s.get("type",""), "file": s.get("file",""), "line": s.get("line",0), "doc": (s.get("doc","") or "")[:60], "params": s.get("params",[])[:3]}
        for s in all_symbols if isinstance(s, dict)
    ][:600])
    call_graph_json = json.dumps(call_graph)
    file_deps_json = json.dumps(file_deps)
    type_counts_json = json.dumps(type_counts)
    lang_counts_json = json.dumps(language_counts)
    type_colors_json = json.dumps(TYPE_COLORS)
    lang_colors_json = json.dumps(LANG_COLORS)
    
    # Build JavaScript with data
    js_code = JS_TEMPLATE.format(
        call_graph_json=call_graph_json,
        file_deps_json=file_deps_json,
        type_counts_json=type_counts_json,
        lang_counts_json=lang_counts_json,
        type_colors_json=type_colors_json,
        lang_colors_json=lang_colors_json,
        search_data_json=search_data_json,
    )
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} — CortexCode Report</title>
    <script src="{d3_src}"></script>
    <style>{CSS_TEMPLATE}</style>
</head>
<body>
    <div class="sidebar">
        <div class="logo"><div class="logo-icon">C</div> CortexCode</div>
        
        <div class="sidebar-stats">
            <div class="sidebar-stat"><div class="sidebar-stat-val">{len(files)}</div><div class="sidebar-stat-lbl">Files</div></div>
            <div class="sidebar-stat"><div class="sidebar-stat-val">{len(all_symbols)}</div><div class="sidebar-stat-lbl">Symbols</div></div>
            <div class="sidebar-stat"><div class="sidebar-stat-val">{non_empty_calls}</div><div class="sidebar-stat-lbl">Linked</div></div>
            <div class="sidebar-stat"><div class="sidebar-stat-val">{len(file_deps)}</div><div class="sidebar-stat-lbl">Deps</div></div>
        </div>
        
        <div class="nav-section">
            <div class="nav-title">Dashboard</div>
            <div class="nav-item active" onclick="showTab('overview', this)">📊 Overview</div>
            <div class="nav-item" onclick="showTab('symbols', this)">⚡ Symbols <span class="badge">{len(all_symbols)}</span></div>
            <div class="nav-item" onclick="showTab('graph', this)">🔗 Call Graph <span class="badge">{non_empty_calls}</span></div>
            <div class="nav-item" onclick="showTab('deps', this)">🌐 File Deps <span class="badge">{len(file_deps)}</span></div>
        </div>
        <div class="nav-section">
            <div class="nav-title">Explore</div>
            <div class="nav-item" onclick="showTab('structure', this)">📁 Files <span class="badge">{len(files)}</span></div>
            <div class="nav-item" onclick="showTab('imports', this)">📥 Imports <span class="badge">{len(all_imports)}</span></div>
            <div class="nav-item" onclick="showTab('exports', this)">📤 Exports <span class="badge">{len(all_exports)}</span></div>
            <div class="nav-item" onclick="showTab('routes', this)">🔌 API Routes <span class="badge">{len(all_api_routes)}</span></div>
            <div class="nav-item" onclick="showTab('entities', this)">🗄️ Entities <span class="badge">{len(all_entities)}</span></div>
        </div>
        <div class="nav-section">
            <div class="nav-title">Docs</div>
            <div class="nav-item" onclick="window.open('README.md','_blank')">📖 README</div>
            <div class="nav-item" onclick="window.open('API.md','_blank')">📑 API Docs</div>
            <div class="nav-item" onclick="window.open('FLOWS.md','_blank')">🔀 Call Flows</div>
        </div>
    </div>
    
    <div class="main">
        <div class="header">
            <div>
                <h1 class="project-name">{project_name}</h1>
                <p class="last-indexed">Indexed {last_indexed[:19] if last_indexed else 'N/A'} · {len(index.get("languages", []))} languages</p>
            </div>
            <div class="search-wrapper">
                <span class="search-icon">🔍</span>
                <input type="text" id="globalSearchInput" class="search-box" placeholder="Search symbols, files..." onkeyup="doGlobalSearch(this.value)" autocomplete="off">
                <div class="search-results" id="searchResults"></div>
            </div>
        </div>
        
        <!-- OVERVIEW TAB -->
        <div id="overview" class="tab-content active">
            <div class="dash-stats">
                <div class="dash-stat">
                    <div class="dash-stat-icon">📄</div>
                    <div class="dash-stat-val">{len(files)}</div>
                    <div class="dash-stat-lbl">Source Files</div>
                </div>
                <div class="dash-stat">
                    <div class="dash-stat-icon">⚡</div>
                    <div class="dash-stat-val">{len(all_symbols)}</div>
                    <div class="dash-stat-lbl">Symbols</div>
                </div>
                <div class="dash-stat">
                    <div class="dash-stat-icon">🔗</div>
                    <div class="dash-stat-val">{total_call_edges}</div>
                    <div class="dash-stat-lbl">Call Edges</div>
                </div>
                <div class="dash-stat">
                    <div class="dash-stat-icon">🌐</div>
                    <div class="dash-stat-val">{len(file_deps)}</div>
                    <div class="dash-stat-lbl">File Dependencies</div>
                </div>
            </div>
            
            <div class="charts-row">
                <div class="card">
                    <div class="card-title">Symbol Types</div>
                    <div class="card-subtitle">{len(all_symbols)} symbols across {len(type_counts)} types</div>
                    <div class="chart-container">
                        <svg id="typeDonut" class="chart-svg" width="160" height="160"></svg>
                        <div class="chart-legend" id="typeLegend"></div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-title">Languages</div>
                    <div class="card-subtitle">{len(files)} files across {len(language_counts)} extensions</div>
                    <div class="chart-container">
                        <svg id="langDonut" class="chart-svg" width="160" height="160"></svg>
                        <div class="chart-legend" id="langLegend"></div>
                    </div>
                </div>
            </div>
            
            <div class="charts-row">
                <div class="card">
                    <div class="card-title">Top Files by Symbols</div>
                    <table class="mini-table">
                        <thead><tr><th>File</th><th style="width:50px;">Count</th><th style="width:120px;"></th></tr></thead>
                        <tbody>{top_files_rows}</tbody>
                    </table>
                </div>
                <div class="card">
                    <div class="card-title">Top Callers</div>
                    <div class="card-subtitle">Functions that call the most other functions</div>
                    <table class="mini-table">
                        <thead><tr><th>Symbol</th><th style="width:50px;">Calls</th><th style="width:120px;"></th></tr></thead>
                        <tbody>{top_callers_rows}</tbody>
                    </table>
                </div>
            </div>
            
            {fw_cards_html}
        </div>
        
        <!-- SYMBOLS TAB -->
        <div id="symbols" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">All Symbols</div>
                        <div class="card-subtitle">{len(all_symbols)} symbols extracted from {len(files)} files</div>
                    </div>
                    <input type="text" class="search-box" style="width:260px;padding-left:14px;" placeholder="Filter symbols..." onkeyup="filterSymbols(this.value)">
                </div>
                <div class="filter-tabs" id="symbolFilterTabs">
                    <div class="filter-tab active" onclick="filterByType('all', this)">All ({len(all_symbols)})</div>
                    {filter_tabs_html}
                </div>
                <div class="symbol-grid" id="symbolGrid">
                    {generate_symbols_html(all_symbols[:200])}
                </div>
                {f'<p style="color:var(--text3);margin-top:16px;font-size:13px;">Showing 200 of {len(all_symbols)} symbols — use search to find more</p>' if len(all_symbols) > 200 else ''}
            </div>
        </div>
        
        <!-- CALL GRAPH TAB -->
        <div id="graph" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Call Graph</div>
                        <div class="card-subtitle">{non_empty_calls} symbols with {total_call_edges} call edges — click a node to explore</div>
                    </div>
                </div>
                <div class="graph-controls">
                    <input type="text" class="graph-search" id="graphSearch" placeholder="Search node..." oninput="searchGraphNode(this.value)">
                    <div class="graph-btn" onclick="resetGraph()">Reset</div>
                    <div class="graph-btn" onclick="zoomIn()">Zoom +</div>
                    <div class="graph-btn" onclick="zoomOut()">Zoom −</div>
                    <div class="graph-btn" id="toggleLabels" onclick="toggleLabels()">Hide Labels</div>
                    <span style="margin-left:auto;font-size:12px;color:var(--text3);" id="graphNodeCount"></span>
                </div>
                <div class="graph-container" id="graphContainer">
                    <div class="graph-tooltip" id="graphTooltip"></div>
                </div>
                <div class="graph-info" id="graphInfo"></div>
            </div>
        </div>
        
        <!-- FILE DEPS TAB -->
        <div id="deps" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">File Dependency Graph</div>
                        <div class="card-subtitle">{len(file_deps)} files with tracked import relationships</div>
                    </div>
                </div>
                <div class="graph-controls">
                    <input type="text" class="graph-search" id="depsSearch" placeholder="Search file..." oninput="searchDepsNode(this.value)">
                    <div class="graph-btn" onclick="resetDeps()">Reset</div>
                </div>
                <div class="deps-container" id="depsContainer"></div>
                <div class="graph-info" id="depsInfo"></div>
            </div>
        </div>
        
        <!-- STRUCTURE TAB -->
        <div id="structure" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">File Tree</div>
                    <input type="text" class="search-box" style="width:260px;padding-left:14px;" placeholder="Filter files..." onkeyup="filterTree(this.value)">
                </div>
                <div class="tree-view" id="fileTree">{generate_tree_html(file_tree, 0)}</div>
            </div>
        </div>
        
        <!-- IMPORTS TAB -->
        <div id="imports" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Imports ({len(all_imports)})</div>
                </div>
                <div class="filter-tabs">
                    <div class="filter-tab active" onclick="filterImports('all', this)">All</div>
                    <div class="filter-tab" onclick="filterImports('external', this)">External</div>
                    <div class="filter-tab" onclick="filterImports('internal', this)">Internal</div>
                </div>
                <div class="symbol-grid">{generate_imports_html(all_imports[:80])}</div>
            </div>
        </div>
        
        <!-- EXPORTS TAB -->
        <div id="exports" class="tab-content">
            <div class="card">
                <div class="card-title">Exports ({len(all_exports)})</div>
                <div class="symbol-grid" style="margin-top:16px;">{generate_exports_html(all_exports[:80])}</div>
            </div>
        </div>
        
        <!-- API ROUTES TAB -->
        <div id="routes" class="tab-content">
            <div class="card">
                <div class="card-title">API Routes ({len(all_api_routes)})</div>
                <div class="symbol-grid" style="margin-top:16px;">{generate_routes_html(all_api_routes[:80])}</div>
            </div>
        </div>
        
        <!-- ENTITIES TAB -->
        <div id="entities" class="tab-content">
            <div class="card">
                <div class="card-title">Database Entities ({len(all_entities)})</div>
                <div class="symbol-grid" style="margin-top:16px;">{generate_entities_html(all_entities[:80])}</div>
            </div>
        </div>
    </div>
    
    <!-- Symbol Detail Modal -->
    <div class="modal" id="symbolModal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title" id="modalTitle"></div>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div id="modalBody"></div>
        </div>
    </div>
    
    <script>{js_code}</script>
</body>
</html>"""
    
    output_path.write_text(html, encoding="utf-8")
