"""HTML/CSS templates for documentation."""

D3_CDN_URL = "https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"

CSS_TEMPLATE = """
:root {
    --bg: #0f172a; --bg2: #1e293b; --bg3: #334155;
    --text: #e2e8f0; --text2: #94a3b8; --text3: #64748b;
    --accent: #38bdf8; --accent2: #818cf8; --green: #34d399;
    --yellow: #fbbf24; --red: #f87171; --pink: #f472b6;
    --radius: 12px; --radius-sm: 8px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }

.sidebar {
    position: fixed; left: 0; top: 0; width: 260px; height: 100vh;
    background: var(--bg2); border-right: 1px solid var(--bg3); overflow-y: auto;
    padding: 20px; z-index: 50;
}
.sidebar::-webkit-scrollbar { width: 4px; }
.sidebar::-webkit-scrollbar-thumb { background: var(--bg3); border-radius: 4px; }

.logo { font-size: 20px; font-weight: 700; color: var(--accent); margin-bottom: 24px; display: flex; align-items: center; gap: 10px; }
.logo-icon { width: 32px; height: 32px; background: linear-gradient(135deg, #38bdf8, #818cf8); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 900; color: white; font-size: 14px; }

.sidebar-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 20px; }
.sidebar-stat { background: var(--bg); padding: 12px 10px; border-radius: var(--radius-sm); text-align: center; }
.sidebar-stat-val { font-size: 22px; font-weight: 700; color: var(--accent); }
.sidebar-stat-lbl { font-size: 10px; color: var(--text3); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }

.nav-section { margin-bottom: 16px; }
.nav-title { font-size: 10px; text-transform: uppercase; color: var(--text3); letter-spacing: 1px; margin-bottom: 8px; font-weight: 600; }
.nav-item { display: flex; align-items: center; gap: 10px; padding: 9px 12px; border-radius: var(--radius-sm); cursor: pointer; transition: all 0.15s; color: var(--text2); font-size: 13px; }
.nav-item:hover { background: var(--bg3); color: var(--text); }
.nav-item.active { background: var(--accent); color: white; font-weight: 600; }
.nav-item .badge { margin-left: auto; background: var(--bg); color: var(--text3); padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.nav-item.active .badge { background: rgba(255,255,255,0.2); color: white; }

.main { margin-left: 260px; padding: 24px 30px; min-height: 100vh; }

.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; gap: 20px; }
.project-name { font-size: 26px; font-weight: 700; }
.last-indexed { color: var(--text3); font-size: 13px; margin-top: 4px; }

.search-wrapper { position: relative; flex-shrink: 0; }
.search-box { background: var(--bg2); border: 1px solid var(--bg3); border-radius: var(--radius-sm); padding: 10px 14px 10px 36px; color: white; width: 360px; font-size: 13px; transition: border 0.15s; }
.search-box:focus { outline: none; border-color: var(--accent); }
.search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text3); font-size: 14px; pointer-events: none; }
.search-results { display: none; position: absolute; top: 100%; right: 0; width: 460px; max-height: 400px; overflow-y: auto; background: var(--bg2); border: 1px solid var(--bg3); border-radius: var(--radius-sm); z-index: 100; margin-top: 4px; box-shadow: 0 8px 30px rgba(0,0,0,0.4); }
.search-result-item { display: flex; align-items: center; gap: 10px; padding: 10px 14px; cursor: pointer; border-bottom: 1px solid var(--bg3); font-size: 13px; }
.search-result-item:hover { background: var(--bg3); }
.search-result-item:last-child { border-bottom: none; }

.tab-content { display: none; }
.tab-content.active { display: block; }

.card { background: var(--bg2); border-radius: var(--radius); padding: 24px; margin-bottom: 16px; border: 1px solid var(--bg3); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card-title { font-size: 16px; font-weight: 600; }
.card-subtitle { font-size: 12px; color: var(--text3); margin-top: 4px; }

.dash-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.dash-stat { background: var(--bg2); border: 1px solid var(--bg3); border-radius: var(--radius); padding: 20px; position: relative; overflow: hidden; }
.dash-stat::after { content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; }
.dash-stat:nth-child(1)::after { background: var(--accent); }
.dash-stat:nth-child(2)::after { background: var(--green); }
.dash-stat:nth-child(3)::after { background: var(--yellow); }
.dash-stat:nth-child(4)::after { background: var(--accent2); }
.dash-stat-icon { font-size: 28px; margin-bottom: 8px; }
.dash-stat-val { font-size: 32px; font-weight: 700; }
.dash-stat:nth-child(1) .dash-stat-val { color: var(--accent); }
.dash-stat:nth-child(2) .dash-stat-val { color: var(--green); }
.dash-stat:nth-child(3) .dash-stat-val { color: var(--yellow); }
.dash-stat:nth-child(4) .dash-stat-val { color: var(--accent2); }
.dash-stat-lbl { font-size: 12px; color: var(--text3); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }

.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.chart-container { display: flex; align-items: center; justify-content: center; gap: 24px; padding: 10px 0; }
.chart-svg { flex-shrink: 0; }
.chart-legend { display: flex; flex-direction: column; gap: 6px; }
.chart-legend-item { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text2); }
.chart-legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.chart-legend-val { margin-left: auto; font-weight: 600; color: var(--text); min-width: 28px; text-align: right; }

.mini-table { width: 100%; }
.mini-table th { text-align: left; font-size: 11px; color: var(--text3); text-transform: uppercase; letter-spacing: 0.5px; padding: 8px 0; border-bottom: 1px solid var(--bg3); }
.mini-table td { padding: 8px 0; font-size: 13px; border-bottom: 1px solid rgba(51,65,85,0.5); }
.mini-table tr:last-child td { border-bottom: none; }
.mini-table .bar { height: 6px; background: var(--accent); border-radius: 3px; min-width: 4px; }

.tree-view { font-family: 'Fira Code', 'Cascadia Code', monospace; font-size: 13px; }
.tree-item { padding: 6px 12px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: background 0.1s; }
.tree-item:hover { background: var(--bg3); }
.tree-item.folder { color: var(--yellow); }
.tree-item.file { color: var(--text2); }
.tree-count { margin-left: auto; color: var(--text3); font-size: 11px; }

.symbol-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.symbol-card { background: var(--bg); border-radius: var(--radius-sm); padding: 16px; border: 1px solid var(--bg3); transition: all 0.15s; cursor: pointer; }
.symbol-card:hover { border-color: var(--accent); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(56,189,248,0.1); }
.symbol-name { font-size: 14px; font-weight: 600; color: var(--accent); margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.symbol-meta { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; }
.badge-type { background: var(--bg3); color: var(--text2); }
.badge-fw { background: #7c3aed; color: white; }
.badge-doc { background: rgba(52,211,153,0.2); color: var(--green); }
.symbol-file { font-size: 11px; color: var(--text3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.symbol-params { font-size: 12px; color: var(--text2); font-family: 'Fira Code', monospace; margin-top: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.filter-tabs { display: flex; gap: 6px; margin-bottom: 16px; flex-wrap: wrap; }
.filter-tab { padding: 6px 14px; background: var(--bg); border: 1px solid var(--bg3); border-radius: 20px; cursor: pointer; color: var(--text2); font-size: 12px; transition: all 0.15s; }
.filter-tab:hover { border-color: var(--accent); color: var(--text); }
.filter-tab.active { background: var(--accent); color: white; border-color: var(--accent); }

.graph-controls { display: flex; gap: 8px; margin-bottom: 12px; align-items: center; flex-wrap: wrap; }
.graph-btn { padding: 6px 14px; background: var(--bg); border: 1px solid var(--bg3); border-radius: var(--radius-sm); cursor: pointer; color: var(--text2); font-size: 12px; transition: all 0.15s; }
.graph-btn:hover { border-color: var(--accent); color: var(--text); }
.graph-btn.active { background: var(--accent); color: white; border-color: var(--accent); }
.graph-search { background: var(--bg); border: 1px solid var(--bg3); border-radius: var(--radius-sm); padding: 6px 12px; color: white; font-size: 12px; width: 200px; }
.graph-search:focus { outline: none; border-color: var(--accent); }
.graph-container { width: 100%; height: 600px; background: var(--bg); border-radius: var(--radius-sm); position: relative; overflow: hidden; }
.graph-container svg { width: 100%; height: 100%; }
.graph-tooltip { position: absolute; background: var(--bg2); border: 1px solid var(--bg3); border-radius: var(--radius-sm); padding: 12px; font-size: 12px; pointer-events: none; z-index: 10; display: none; max-width: 300px; box-shadow: 0 4px 20px rgba(0,0,0,0.4); }
.graph-info { margin-top: 12px; padding: 16px; background: var(--bg); border-radius: var(--radius-sm); display: none; }
.graph-info.active { display: block; }

.link { stroke-opacity: 0.4; }
.link.highlighted { stroke-opacity: 1; stroke: var(--accent); stroke-width: 2.5; }
.node circle { transition: r 0.2s; }
.node.dimmed circle { opacity: 0.15; }
.node.dimmed text { opacity: 0.15; }
.link.dimmed { stroke-opacity: 0.05; }

.deps-container { width: 100%; height: 500px; background: var(--bg); border-radius: var(--radius-sm); position: relative; overflow: hidden; }
.deps-container svg { width: 100%; height: 100%; }

.modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1000; backdrop-filter: blur(4px); }
.modal.active { display: flex; align-items: center; justify-content: center; }
.modal-content { background: var(--bg2); border-radius: var(--radius); padding: 28px; max-width: 640px; width: 90%; max-height: 80vh; overflow-y: auto; border: 1px solid var(--bg3); box-shadow: 0 20px 60px rgba(0,0,0,0.5); }
.modal-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.modal-title { font-size: 22px; font-weight: 700; color: var(--accent); }
.modal-close { background: none; border: none; color: var(--text3); font-size: 22px; cursor: pointer; padding: 4px 8px; border-radius: 6px; }
.modal-close:hover { background: var(--bg3); color: var(--text); }
.modal-section { margin-bottom: 16px; }
.modal-section-title { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--text3); margin-bottom: 8px; font-weight: 600; }
.modal-code { background: var(--bg); padding: 10px 14px; border-radius: var(--radius-sm); font-family: 'Fira Code', monospace; font-size: 13px; }
.modal-tag { display: inline-block; background: var(--bg); padding: 4px 10px; border-radius: 6px; margin: 2px; font-size: 12px; color: var(--text2); border: 1px solid var(--bg3); cursor: pointer; }
.modal-tag:hover { border-color: var(--accent); color: var(--accent); }

@media (max-width: 1200px) {
    .dash-stats { grid-template-columns: repeat(2, 1fr); }
    .charts-row { grid-template-columns: 1fr; }
}
"""

TYPE_COLORS = {
    "function": "#38bdf8",
    "class": "#a78bfa",
    "method": "#34d399",
    "interface": "#fbbf24",
    "type": "#f472b6",
    "enum": "#fb923c",
}

LANG_COLORS = {
    ".ts": "#3178c6", ".tsx": "#3178c6",
    ".js": "#f7df1e", ".jsx": "#f7df1e",
    ".py": "#3572A5",
    ".go": "#00ADD8",
    ".rs": "#dea584",
    ".java": "#b07219",
    ".cs": "#178600",
}
