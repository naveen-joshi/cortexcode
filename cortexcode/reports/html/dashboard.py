import json
from pathlib import Path
from typing import Any

from cortexcode.docs.html_generators import (
    generate_entities_html,
    generate_exports_html,
    generate_imports_html,
    generate_routes_html,
    generate_symbols_html,
    generate_tree_html,
)
from cortexcode.docs.javascript import JS_TEMPLATE
from cortexcode.docs.templates import CSS_TEMPLATE, D3_CDN_URL, LANG_COLORS, TYPE_COLORS
from cortexcode.reports.html.dashboard_fragments import (
    build_dashboard_js_code,
    build_filter_tabs_html,
    build_framework_cards_html,
    build_insight_cards_html,
    build_layer_cards_html,
    build_top_callers_rows_html,
    build_top_files_rows_html,
)
from cortexcode.reports.html.view_model import build_dashboard_view_model


def generate_html_docs(index: dict[str, Any], output_path: Path, d3_src: str = D3_CDN_URL) -> None:
    view_model = build_dashboard_view_model(index)
    files = view_model["files"]
    call_graph = view_model["call_graph"]
    file_deps = view_model["file_deps"]
    project_root = view_model["project_root"]
    last_indexed = view_model["last_indexed"]
    project_profile = view_model["project_profile"]
    all_symbols = view_model["all_symbols"]
    file_tree = view_model["file_tree"]
    framework_counts = view_model["framework_counts"]
    language_counts = view_model["language_counts"]
    type_counts = view_model["type_counts"]
    all_imports = view_model["all_imports"]
    all_exports = view_model["all_exports"]
    all_api_routes = view_model["all_api_routes"]
    all_entities = view_model["all_entities"]
    files_with_most_symbols = view_model["files_with_most_symbols"]
    profile_frameworks = view_model["profile_frameworks"]
    profile_layers = view_model["profile_layers"]
    profile_entry_points = view_model["profile_entry_points"]
    profile_recommendations = view_model["profile_recommendations"]
    non_empty_calls = view_model["non_empty_calls"]
    total_call_edges = view_model["total_call_edges"]
    top_callers = view_model["top_callers"]
    project_name = view_model["project_name"]

    fw_cards_html = build_framework_cards_html(profile_frameworks, framework_counts)
    layer_cards_html = build_layer_cards_html(profile_layers)
    insight_cards_html = build_insight_cards_html(profile_entry_points, profile_recommendations)
    filter_tabs_html = build_filter_tabs_html(type_counts)
    top_files_rows = build_top_files_rows_html(files_with_most_symbols)
    top_callers_rows = build_top_callers_rows_html(top_callers)

    js_code = build_dashboard_js_code(
        call_graph=call_graph,
        file_deps=file_deps,
        type_counts=type_counts,
        language_counts=language_counts,
        type_colors=TYPE_COLORS,
        lang_colors=LANG_COLORS,
        all_symbols=all_symbols,
        js_template=JS_TEMPLATE,
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} — CortexCode Report</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="{d3_src}"></script>
    <style>{CSS_TEMPLATE}</style>
</head>
<body>
    <div class="sidebar">
        <div class="logo"><div class="logo-icon">CC</div> <span class="logo-text">CortexCode</span></div>
        
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
            <div class="nav-item" onclick="window.open('TECH.md','_blank')">🧭 Tech Profile</div>
            <div class="nav-item" onclick="window.open('INSIGHTS.md','_blank')">💡 Insights</div>
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
            {layer_cards_html}
            {insight_cards_html}
        </div>
        
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
        
        <div id="structure" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">File Tree</div>
                    <input type="text" class="search-box" style="width:260px;padding-left:14px;" placeholder="Filter files..." onkeyup="filterTree(this.value)">
                </div>
                <div class="tree-view" id="fileTree">{generate_tree_html(file_tree, 0)}</div>
            </div>
        </div>
        
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
        
        <div id="exports" class="tab-content">
            <div class="card">
                <div class="card-title">Exports ({len(all_exports)})</div>
                <div class="symbol-grid" style="margin-top:16px;">{generate_exports_html(all_exports[:80])}</div>
            </div>
        </div>
        
        <div id="routes" class="tab-content">
            <div class="card">
                <div class="card-title">API Routes ({len(all_api_routes)})</div>
                <div class="symbol-grid" style="margin-top:16px;">{generate_routes_html(all_api_routes[:80])}</div>
            </div>
        </div>
        
        <div id="entities" class="tab-content">
            <div class="card">
                <div class="card-title">Database Entities ({len(all_entities)})</div>
                <div class="symbol-grid" style="margin-top:16px;">{generate_entities_html(all_entities[:80])}</div>
            </div>
        </div>
    </div>
    
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
