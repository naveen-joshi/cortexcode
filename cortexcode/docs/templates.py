"""HTML/CSS templates for documentation."""

D3_CDN_URL = "https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"

CSS_TEMPLATE = """
:root {
    --bg: #0a0a0f; --bg2: #12121a; --bg3: #1e1e2e; --bg4: #2a2a3d;
    --text: #f0f0f5; --text2: #8888a0; --text3: #555566;
    --accent: #00d4ff; --accent2: #a855f7; --green: #10b981;
    --yellow: #f59e0b; --red: #f87171; --pink: #ec4899;
    --glass-border: rgba(255, 255, 255, 0.06);
    --glass-bg: rgba(18, 18, 26, 0.7);
    --shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    --radius: 16px; --radius-sm: 10px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
}

.sidebar {
    position: fixed; left: 0; top: 0; width: 270px; height: 100vh;
    background: var(--bg2); border-right: 1px solid var(--glass-border);
    overflow-y: auto; padding: 24px; z-index: 50;
    backdrop-filter: blur(12px);
}
.sidebar::-webkit-scrollbar { width: 4px; }
.sidebar::-webkit-scrollbar-thumb { background: var(--bg4); border-radius: 4px; }

.logo { font-size: 20px; font-weight: 700; margin-bottom: 28px; display: flex; align-items: center; gap: 12px; }
.logo-text { background: linear-gradient(135deg, var(--accent), var(--accent2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.logo-icon { width: 36px; height: 36px; background: linear-gradient(135deg, var(--accent), var(--accent2)); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 800; color: white; font-size: 14px; }

.sidebar-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 24px; }
.sidebar-stat { background: var(--glass-bg); border: 1px solid var(--glass-border); backdrop-filter: blur(12px); padding: 14px 12px; border-radius: var(--radius-sm); text-align: center; }
.sidebar-stat-val { font-size: 24px; font-weight: 700; color: var(--accent); font-family: 'JetBrains Mono', monospace; }
.sidebar-stat-lbl { font-size: 10px; color: var(--text3); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }

.nav-section { margin-bottom: 20px; }
.nav-title { font-size: 10px; text-transform: uppercase; color: var(--text3); letter-spacing: 1px; margin-bottom: 8px; font-weight: 600; }
.nav-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: var(--radius-sm); cursor: pointer; transition: all 0.2s; color: var(--text2); font-size: 13px; border: 1px solid transparent; }
.nav-item:hover { background: var(--bg3); color: var(--text); }
.nav-item.active { background: linear-gradient(135deg, rgba(0,212,255,0.12), rgba(168,85,247,0.12)); color: var(--accent); border-color: rgba(0,212,255,0.25); font-weight: 600; }
.nav-item .badge { margin-left: auto; background: var(--bg); color: var(--text3); padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.nav-item.active .badge { background: rgba(0,212,255,0.15); color: var(--accent); }

.main {
    margin-left: 270px; padding: 28px 32px; min-height: 100vh;
    background:
        radial-gradient(ellipse at 20% 10%, rgba(0,212,255,0.04) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 90%, rgba(168,85,247,0.04) 0%, transparent 50%),
        var(--bg);
}

.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 28px; gap: 20px; }
.project-name { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, var(--text), var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.last-indexed { color: var(--text3); font-size: 13px; margin-top: 4px; -webkit-text-fill-color: var(--text3); }

.search-wrapper { position: relative; flex-shrink: 0; }
.search-box { background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: var(--radius-sm); padding: 11px 14px 11px 36px; color: var(--text); width: 360px; font-size: 13px; transition: all 0.2s; backdrop-filter: blur(12px); font-family: inherit; }
.search-box:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 20px rgba(0,212,255,0.1); }
.search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text3); font-size: 14px; pointer-events: none; }
.search-results { display: none; position: absolute; top: 100%; right: 0; width: 460px; max-height: 400px; overflow-y: auto; background: var(--bg2); border: 1px solid var(--glass-border); border-radius: var(--radius-sm); z-index: 100; margin-top: 6px; box-shadow: var(--shadow); backdrop-filter: blur(12px); }
.search-result-item { display: flex; align-items: center; gap: 10px; padding: 12px 16px; cursor: pointer; border-bottom: 1px solid var(--glass-border); font-size: 13px; transition: background 0.15s; }
.search-result-item:hover { background: var(--bg3); }
.search-result-item:last-child { border-bottom: none; }

.tab-content { display: none; }
.tab-content.active { display: block; }

.card { background: var(--glass-bg); border-radius: var(--radius); padding: 24px; margin-bottom: 16px; border: 1px solid var(--glass-border); backdrop-filter: blur(12px); box-shadow: var(--shadow); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card-title { font-size: 16px; font-weight: 600; }
.card-subtitle { font-size: 12px; color: var(--text3); margin-top: 4px; }

.dash-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 20px; }
.dash-stat { background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: var(--radius); padding: 22px; position: relative; overflow: hidden; backdrop-filter: blur(12px); box-shadow: var(--shadow); transition: transform 0.2s, box-shadow 0.2s; }
.dash-stat:hover { transform: translateY(-2px); box-shadow: 0 12px 40px rgba(0,0,0,0.5); }
.dash-stat::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
.dash-stat:nth-child(1)::before { background: linear-gradient(90deg, var(--accent), transparent); }
.dash-stat:nth-child(2)::before { background: linear-gradient(90deg, var(--green), transparent); }
.dash-stat:nth-child(3)::before { background: linear-gradient(90deg, var(--yellow), transparent); }
.dash-stat:nth-child(4)::before { background: linear-gradient(90deg, var(--accent2), transparent); }
.dash-stat-icon { font-size: 28px; margin-bottom: 10px; }
.dash-stat-val { font-size: 34px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.dash-stat:nth-child(1) .dash-stat-val { color: var(--accent); }
.dash-stat:nth-child(2) .dash-stat-val { color: var(--green); }
.dash-stat:nth-child(3) .dash-stat-val { color: var(--yellow); }
.dash-stat:nth-child(4) .dash-stat-val { color: var(--accent2); }
.dash-stat-lbl { font-size: 11px; color: var(--text3); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }

.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.chart-container { display: flex; align-items: center; justify-content: center; gap: 28px; padding: 12px 0; }
.chart-svg { flex-shrink: 0; }
.chart-legend { display: flex; flex-direction: column; gap: 8px; }
.chart-legend-item { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text2); }
.chart-legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.chart-legend-val { margin-left: auto; font-weight: 600; color: var(--text); min-width: 28px; text-align: right; font-family: 'JetBrains Mono', monospace; font-size: 11px; }

.mini-table { width: 100%; border-collapse: collapse; }
.mini-table th { text-align: left; font-size: 11px; color: var(--text3); text-transform: uppercase; letter-spacing: 0.5px; padding: 10px 0; border-bottom: 1px solid var(--glass-border); }
.mini-table td { padding: 10px 0; font-size: 13px; border-bottom: 1px solid rgba(255,255,255,0.03); }
.mini-table tr:last-child td { border-bottom: none; }
.mini-table tr:hover td { background: rgba(255,255,255,0.02); }
.mini-table .bar { height: 6px; background: linear-gradient(90deg, var(--accent), var(--accent2)); border-radius: 3px; min-width: 4px; }

.tree-view { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px; }
.tree-item { padding: 7px 12px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: all 0.15s; }
.tree-item:hover { background: var(--bg3); }
.tree-item.folder { color: var(--yellow); }
.tree-item.file { color: var(--text2); }
.tree-count { margin-left: auto; color: var(--text3); font-size: 11px; }

.symbol-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.symbol-card { background: var(--bg); border-radius: var(--radius-sm); padding: 16px; border: 1px solid var(--glass-border); transition: all 0.2s; cursor: pointer; }
.symbol-card:hover { border-color: rgba(0,212,255,0.3); transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,212,255,0.08); }
.symbol-name { font-size: 14px; font-weight: 600; color: var(--accent); margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-family: 'JetBrains Mono', monospace; }
.symbol-meta { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.badge { display: inline-block; padding: 3px 9px; border-radius: 10px; font-size: 11px; font-weight: 500; }
.badge-type { background: rgba(255,255,255,0.06); color: var(--text2); }
.badge-fw { background: rgba(168,85,247,0.2); color: var(--accent2); }
.badge-doc { background: rgba(16,185,129,0.15); color: var(--green); }
.symbol-file { font-size: 11px; color: var(--text3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.symbol-params { font-size: 12px; color: var(--text2); font-family: 'JetBrains Mono', monospace; margin-top: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.filter-tabs { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.filter-tab { padding: 7px 16px; background: var(--bg); border: 1px solid var(--glass-border); border-radius: 20px; cursor: pointer; color: var(--text2); font-size: 12px; transition: all 0.2s; }
.filter-tab:hover { border-color: rgba(0,212,255,0.3); color: var(--text); }
.filter-tab.active { background: linear-gradient(135deg, rgba(0,212,255,0.15), rgba(168,85,247,0.15)); color: var(--accent); border-color: rgba(0,212,255,0.3); }

.graph-controls { display: flex; gap: 8px; margin-bottom: 14px; align-items: center; flex-wrap: wrap; }
.graph-btn { padding: 7px 16px; background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: var(--radius-sm); cursor: pointer; color: var(--text2); font-size: 12px; transition: all 0.2s; backdrop-filter: blur(12px); }
.graph-btn:hover { border-color: rgba(0,212,255,0.3); color: var(--text); }
.graph-btn.active { background: linear-gradient(135deg, rgba(0,212,255,0.15), rgba(168,85,247,0.15)); color: var(--accent); border-color: rgba(0,212,255,0.3); }
.graph-search { background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: var(--radius-sm); padding: 7px 12px; color: var(--text); font-size: 12px; width: 220px; font-family: inherit; }
.graph-search:focus { outline: none; border-color: var(--accent); }
.graph-container { width: 100%; height: 600px; background: var(--bg); border-radius: var(--radius-sm); position: relative; overflow: hidden; border: 1px solid var(--glass-border); }
.graph-container svg { width: 100%; height: 100%; }
.graph-tooltip { position: absolute; background: var(--bg2); border: 1px solid var(--glass-border); border-radius: var(--radius-sm); padding: 12px 16px; font-size: 12px; pointer-events: none; z-index: 10; display: none; max-width: 320px; box-shadow: var(--shadow); backdrop-filter: blur(12px); }
.graph-info { margin-top: 12px; padding: 18px; background: var(--glass-bg); border-radius: var(--radius-sm); display: none; border: 1px solid var(--glass-border); }
.graph-info.active { display: block; }

.node-label { font-size: 11px; fill: var(--text2); pointer-events: none; text-shadow: 0 0 4px var(--bg), 0 0 8px var(--bg); }
.link { stroke-opacity: 0.4; }
.link.highlighted { stroke-opacity: 1; stroke: var(--accent); stroke-width: 2.5; }
.node circle { transition: all 0.2s; }
.node.dimmed circle { opacity: 0.12; }
.node.dimmed text { opacity: 0.12; }
.link.dimmed { stroke-opacity: 0.03; }

.deps-container { width: 100%; height: 500px; background: var(--bg); border-radius: var(--radius-sm); position: relative; overflow: hidden; border: 1px solid var(--glass-border); }
.deps-container svg { width: 100%; height: 100%; }

.modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.75); z-index: 1000; backdrop-filter: blur(8px); }
.modal.active { display: flex; align-items: center; justify-content: center; }
.modal-content { background: var(--bg2); border-radius: var(--radius); padding: 28px; max-width: 640px; width: 90%; max-height: 80vh; overflow-y: auto; border: 1px solid var(--glass-border); box-shadow: 0 24px 80px rgba(0,0,0,0.6); }
.modal-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.modal-title { font-size: 22px; font-weight: 700; color: var(--accent); font-family: 'JetBrains Mono', monospace; }
.modal-close { background: none; border: none; color: var(--text3); font-size: 22px; cursor: pointer; padding: 4px 8px; border-radius: 8px; transition: all 0.15s; }
.modal-close:hover { background: var(--bg3); color: var(--text); }
.modal-section { margin-bottom: 16px; }
.modal-section-title { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: var(--text3); margin-bottom: 8px; font-weight: 600; }
.modal-code { background: var(--bg); padding: 12px 16px; border-radius: var(--radius-sm); font-family: 'JetBrains Mono', monospace; font-size: 13px; border: 1px solid var(--glass-border); }
.modal-tag { display: inline-block; background: var(--bg); padding: 4px 10px; border-radius: 8px; margin: 2px; font-size: 12px; color: var(--text2); border: 1px solid var(--glass-border); cursor: pointer; transition: all 0.15s; }
.modal-tag:hover { border-color: rgba(0,212,255,0.3); color: var(--accent); }

@media (max-width: 1200px) {
    .dash-stats { grid-template-columns: repeat(2, 1fr); }
    .charts-row { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
    .sidebar { display: none; }
    .main { margin-left: 0; padding: 16px; }
    .dash-stats { grid-template-columns: 1fr; }
    .search-box { width: 100%; }
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
