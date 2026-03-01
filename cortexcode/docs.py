"""Docs Generator - Generate project documentation from index."""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

D3_CDN_URL = "https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"
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
    
    # Fallback to CDN if download fails
    return D3_CDN_URL


def generate_all_docs(index_path: Path, output_dir: Path) -> None:
    """Generate all documentation files from the index."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    index = json.loads(index_path.read_text(encoding="utf-8"))
    
    # Bundle D3.js locally for offline support
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
    call_graph = index.get("call_graph", {})
    
    lines = [
        "# API Documentation",
        "",
        "## Symbols",
        "",
    ]
    
    all_symbols = []
    
    for rel_path, file_data in files.items():
        symbols = file_data.get("symbols", []) if isinstance(file_data, dict) else file_data
        
        for sym in symbols:
            all_symbols.append(sym)
        
        for sym in symbols:
            name = sym.get("name", "unknown")
            sym_type = sym.get("type", "unknown")
            
            lines.append(f"## {name} (`{rel_path}`)")
            lines.append("")
            lines.append(f"**Type:** {sym_type}")
            
            if sym_type == "function":
                params = sym.get("params", [])
                if params:
                    lines.append(f"**Parameters:** {', '.join(params)}")
            
            if sym_type == "class":
                methods = sym.get("methods", [])
                if methods:
                    lines.append("")
                    lines.append("### Methods")
                    for method in methods:
                        m_params = method.get("params", [])
                        params_str = f"({', '.join(m_params)})" if m_params else "()"
                        lines.append(f"- `{method['name']}{params_str}`")
            
            calls = sym.get("calls", [])
            if calls:
                lines.append("")
                lines.append("### Calls")
                for call in calls:
                    lines.append(f"- `{call}`")
            
            callers = [s for s, c in call_graph.items() if name in c]
            if callers:
                lines.append("")
                lines.append("### Called By")
                for caller in callers:
                    lines.append(f"- `{caller}`")
            
            lines.append("")
    
    output_path.write_text("\n".join(lines), encoding="utf-8")


def generate_structure_docs(index: dict, output_path: Path) -> None:
    """Generate directory structure documentation."""
    files = index.get("files", {})
    
    tree = defaultdict(lambda: defaultdict(list))
    
    for rel_path, file_data in files.items():
        symbols = file_data.get("symbols", []) if isinstance(file_data, dict) else file_data
        parts = Path(rel_path).parts
        if len(parts) == 1:
            tree["."][rel_path] = symbols
        else:
            tree[parts[0]]["/".join(parts[1:])] = symbols
    
    lines = [
        "# Directory Structure",
        "",
        "```",
    ]
    
    all_paths = sorted(files.keys())
    for path in all_paths:
        parts = path.split("/")
        indent = "  " * (len(parts) - 1)
        file_name = parts[-1]
        sym_count = len(files[path])
        lines.append(f"{indent}{file_name} ({sym_count} symbols)")
    
    lines.extend([
        "```",
        "",
        f"**Total files:** {len(files)}",
    ])
    
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
    
    # Compute graph stats
    non_empty_calls = sum(1 for v in call_graph.values() if v)
    total_call_edges = sum(len(v) for v in call_graph.values() if v)
    top_callers = sorted(
        [(k, len(v)) for k, v in call_graph.items() if v],
        key=lambda x: x[1], reverse=True
    )[:10]
    
    # Type colors for charts
    type_colors = {
        "function": "#38bdf8",
        "class": "#a78bfa",
        "method": "#34d399",
        "interface": "#fbbf24",
        "type": "#f472b6",
        "enum": "#fb923c",
    }
    lang_colors = {
        ".ts": "#3178c6", ".tsx": "#3178c6",
        ".js": "#f7df1e", ".jsx": "#f7df1e",
        ".py": "#3572A5",
        ".go": "#00ADD8",
        ".rs": "#dea584",
        ".java": "#b07219",
        ".cs": "#178600",
    }
    
    project_name = Path(project_root).name
    
    # Pre-build HTML fragments that have complex quoting
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
    
    # Pre-build JSON data for JavaScript
    search_data_json = json.dumps([
        {"name": s.get("name",""), "type": s.get("type",""), "file": s.get("file",""), "line": s.get("line",0), "doc": (s.get("doc","") or "")[:60], "params": s.get("params",[])[:3]}
        for s in all_symbols if isinstance(s, dict)
    ][:600])
    call_graph_json = json.dumps(call_graph)
    file_deps_json = json.dumps(file_deps)
    type_counts_json = json.dumps(type_counts)
    lang_counts_json = json.dumps(language_counts)
    type_colors_json = json.dumps(type_colors)
    lang_colors_json = json.dumps(lang_colors)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} — CortexCode Report</title>
    <script src="{d3_src}"></script>
    <style>
        :root {{
            --bg: #0f172a; --bg2: #1e293b; --bg3: #334155;
            --text: #e2e8f0; --text2: #94a3b8; --text3: #64748b;
            --accent: #38bdf8; --accent2: #818cf8; --green: #34d399;
            --yellow: #fbbf24; --red: #f87171; --pink: #f472b6;
            --radius: 12px; --radius-sm: 8px;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }}
        
        .sidebar {{
            position: fixed; left: 0; top: 0; width: 260px; height: 100vh;
            background: var(--bg2); border-right: 1px solid var(--bg3); overflow-y: auto;
            padding: 20px; z-index: 50;
        }}
        .sidebar::-webkit-scrollbar {{ width: 4px; }}
        .sidebar::-webkit-scrollbar-thumb {{ background: var(--bg3); border-radius: 4px; }}
        
        .logo {{ font-size: 20px; font-weight: 700; color: var(--accent); margin-bottom: 24px; display: flex; align-items: center; gap: 10px; }}
        .logo-icon {{ width: 32px; height: 32px; background: linear-gradient(135deg, #38bdf8, #818cf8); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 900; color: white; font-size: 14px; }}
        
        .sidebar-stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 20px; }}
        .sidebar-stat {{ background: var(--bg); padding: 12px 10px; border-radius: var(--radius-sm); text-align: center; }}
        .sidebar-stat-val {{ font-size: 22px; font-weight: 700; color: var(--accent); }}
        .sidebar-stat-lbl {{ font-size: 10px; color: var(--text3); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }}
        
        .nav-section {{ margin-bottom: 16px; }}
        .nav-title {{ font-size: 10px; text-transform: uppercase; color: var(--text3); letter-spacing: 1px; margin-bottom: 8px; font-weight: 600; }}
        .nav-item {{ display: flex; align-items: center; gap: 10px; padding: 9px 12px; border-radius: var(--radius-sm); cursor: pointer; transition: all 0.15s; color: var(--text2); font-size: 13px; }}
        .nav-item:hover {{ background: var(--bg3); color: var(--text); }}
        .nav-item.active {{ background: var(--accent); color: white; font-weight: 600; }}
        .nav-item .badge {{ margin-left: auto; background: var(--bg); color: var(--text3); padding: 2px 8px; border-radius: 10px; font-size: 11px; }}
        .nav-item.active .badge {{ background: rgba(255,255,255,0.2); color: white; }}
        
        .main {{ margin-left: 260px; padding: 24px 30px; min-height: 100vh; }}
        
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; gap: 20px; }}
        .project-name {{ font-size: 26px; font-weight: 700; }}
        .last-indexed {{ color: var(--text3); font-size: 13px; margin-top: 4px; }}
        
        .search-wrapper {{ position: relative; flex-shrink: 0; }}
        .search-box {{ background: var(--bg2); border: 1px solid var(--bg3); border-radius: var(--radius-sm); padding: 10px 14px 10px 36px; color: white; width: 360px; font-size: 13px; transition: border 0.15s; }}
        .search-box:focus {{ outline: none; border-color: var(--accent); }}
        .search-icon {{ position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text3); font-size: 14px; pointer-events: none; }}
        .search-results {{ display: none; position: absolute; top: 100%; right: 0; width: 460px; max-height: 400px; overflow-y: auto; background: var(--bg2); border: 1px solid var(--bg3); border-radius: var(--radius-sm); z-index: 100; margin-top: 4px; box-shadow: 0 8px 30px rgba(0,0,0,0.4); }}
        .search-result-item {{ display: flex; align-items: center; gap: 10px; padding: 10px 14px; cursor: pointer; border-bottom: 1px solid var(--bg3); font-size: 13px; }}
        .search-result-item:hover {{ background: var(--bg3); }}
        .search-result-item:last-child {{ border-bottom: none; }}
        
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        
        .card {{ background: var(--bg2); border-radius: var(--radius); padding: 24px; margin-bottom: 16px; border: 1px solid var(--bg3); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }}
        .card-title {{ font-size: 16px; font-weight: 600; }}
        .card-subtitle {{ font-size: 12px; color: var(--text3); margin-top: 4px; }}
        
        /* Dashboard stat cards */
        .dash-stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }}
        .dash-stat {{ background: var(--bg2); border: 1px solid var(--bg3); border-radius: var(--radius); padding: 20px; position: relative; overflow: hidden; }}
        .dash-stat::after {{ content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; }}
        .dash-stat:nth-child(1)::after {{ background: var(--accent); }}
        .dash-stat:nth-child(2)::after {{ background: var(--green); }}
        .dash-stat:nth-child(3)::after {{ background: var(--yellow); }}
        .dash-stat:nth-child(4)::after {{ background: var(--accent2); }}
        .dash-stat-icon {{ font-size: 28px; margin-bottom: 8px; }}
        .dash-stat-val {{ font-size: 32px; font-weight: 700; }}
        .dash-stat:nth-child(1) .dash-stat-val {{ color: var(--accent); }}
        .dash-stat:nth-child(2) .dash-stat-val {{ color: var(--green); }}
        .dash-stat:nth-child(3) .dash-stat-val {{ color: var(--yellow); }}
        .dash-stat:nth-child(4) .dash-stat-val {{ color: var(--accent2); }}
        .dash-stat-lbl {{ font-size: 12px; color: var(--text3); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
        
        /* Charts row */
        .charts-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }}
        .chart-container {{ display: flex; align-items: center; justify-content: center; gap: 24px; padding: 10px 0; }}
        .chart-svg {{ flex-shrink: 0; }}
        .chart-legend {{ display: flex; flex-direction: column; gap: 6px; }}
        .chart-legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text2); }}
        .chart-legend-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
        .chart-legend-val {{ margin-left: auto; font-weight: 600; color: var(--text); min-width: 28px; text-align: right; }}
        
        /* Top files / top callers table */
        .mini-table {{ width: 100%; }}
        .mini-table th {{ text-align: left; font-size: 11px; color: var(--text3); text-transform: uppercase; letter-spacing: 0.5px; padding: 8px 0; border-bottom: 1px solid var(--bg3); }}
        .mini-table td {{ padding: 8px 0; font-size: 13px; border-bottom: 1px solid rgba(51,65,85,0.5); }}
        .mini-table tr:last-child td {{ border-bottom: none; }}
        .mini-table .bar {{ height: 6px; background: var(--accent); border-radius: 3px; min-width: 4px; }}
        
        /* File tree */
        .tree-view {{ font-family: 'Fira Code', 'Cascadia Code', monospace; font-size: 13px; }}
        .tree-item {{ padding: 6px 12px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: background 0.1s; }}
        .tree-item:hover {{ background: var(--bg3); }}
        .tree-item.folder {{ color: var(--yellow); }}
        .tree-item.file {{ color: var(--text2); }}
        .tree-count {{ margin-left: auto; color: var(--text3); font-size: 11px; }}
        
        /* Symbols */
        .symbol-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }}
        .symbol-card {{ background: var(--bg); border-radius: var(--radius-sm); padding: 16px; border: 1px solid var(--bg3); transition: all 0.15s; cursor: pointer; }}
        .symbol-card:hover {{ border-color: var(--accent); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(56,189,248,0.1); }}
        .symbol-name {{ font-size: 14px; font-weight: 600; color: var(--accent); margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .symbol-meta {{ display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; }}
        .badge-type {{ background: var(--bg3); color: var(--text2); }}
        .badge-fw {{ background: #7c3aed; color: white; }}
        .badge-doc {{ background: rgba(52,211,153,0.2); color: var(--green); }}
        .symbol-file {{ font-size: 11px; color: var(--text3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .symbol-params {{ font-size: 12px; color: var(--text2); font-family: 'Fira Code', monospace; margin-top: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        
        .filter-tabs {{ display: flex; gap: 6px; margin-bottom: 16px; flex-wrap: wrap; }}
        .filter-tab {{ padding: 6px 14px; background: var(--bg); border: 1px solid var(--bg3); border-radius: 20px; cursor: pointer; color: var(--text2); font-size: 12px; transition: all 0.15s; }}
        .filter-tab:hover {{ border-color: var(--accent); color: var(--text); }}
        .filter-tab.active {{ background: var(--accent); color: white; border-color: var(--accent); }}
        
        /* Graph */
        .graph-controls {{ display: flex; gap: 8px; margin-bottom: 12px; align-items: center; flex-wrap: wrap; }}
        .graph-btn {{ padding: 6px 14px; background: var(--bg); border: 1px solid var(--bg3); border-radius: var(--radius-sm); cursor: pointer; color: var(--text2); font-size: 12px; transition: all 0.15s; }}
        .graph-btn:hover {{ border-color: var(--accent); color: var(--text); }}
        .graph-btn.active {{ background: var(--accent); color: white; border-color: var(--accent); }}
        .graph-search {{ background: var(--bg); border: 1px solid var(--bg3); border-radius: var(--radius-sm); padding: 6px 12px; color: white; font-size: 12px; width: 200px; }}
        .graph-search:focus {{ outline: none; border-color: var(--accent); }}
        .graph-container {{ width: 100%; height: 600px; background: var(--bg); border-radius: var(--radius-sm); position: relative; overflow: hidden; }}
        .graph-container svg {{ width: 100%; height: 100%; }}
        .graph-tooltip {{ position: absolute; background: var(--bg2); border: 1px solid var(--bg3); border-radius: var(--radius-sm); padding: 12px; font-size: 12px; pointer-events: none; z-index: 10; display: none; max-width: 300px; box-shadow: 0 4px 20px rgba(0,0,0,0.4); }}
        .graph-info {{ margin-top: 12px; padding: 16px; background: var(--bg); border-radius: var(--radius-sm); display: none; }}
        .graph-info.active {{ display: block; }}
        
        .link {{ stroke-opacity: 0.4; }}
        .link.highlighted {{ stroke-opacity: 1; stroke: var(--accent); stroke-width: 2.5; }}
        .node circle {{ transition: r 0.2s; }}
        .node.dimmed circle {{ opacity: 0.15; }}
        .node.dimmed text {{ opacity: 0.15; }}
        .link.dimmed {{ stroke-opacity: 0.05; }}
        
        /* Deps graph */
        .deps-container {{ width: 100%; height: 500px; background: var(--bg); border-radius: var(--radius-sm); position: relative; overflow: hidden; }}
        .deps-container svg {{ width: 100%; height: 100%; }}
        
        /* Modal */
        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1000; backdrop-filter: blur(4px); }}
        .modal.active {{ display: flex; align-items: center; justify-content: center; }}
        .modal-content {{ background: var(--bg2); border-radius: var(--radius); padding: 28px; max-width: 640px; width: 90%; max-height: 80vh; overflow-y: auto; border: 1px solid var(--bg3); box-shadow: 0 20px 60px rgba(0,0,0,0.5); }}
        .modal-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }}
        .modal-title {{ font-size: 22px; font-weight: 700; color: var(--accent); }}
        .modal-close {{ background: none; border: none; color: var(--text3); font-size: 22px; cursor: pointer; padding: 4px 8px; border-radius: 6px; }}
        .modal-close:hover {{ background: var(--bg3); color: var(--text); }}
        .modal-section {{ margin-bottom: 16px; }}
        .modal-section-title {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--text3); margin-bottom: 8px; font-weight: 600; }}
        .modal-code {{ background: var(--bg); padding: 10px 14px; border-radius: var(--radius-sm); font-family: 'Fira Code', monospace; font-size: 13px; }}
        .modal-tag {{ display: inline-block; background: var(--bg); padding: 4px 10px; border-radius: 6px; margin: 2px; font-size: 12px; color: var(--text2); border: 1px solid var(--bg3); cursor: pointer; }}
        .modal-tag:hover {{ border-color: var(--accent); color: var(--accent); }}
        
        /* Responsive */
        @media (max-width: 1200px) {{
            .dash-stats {{ grid-template-columns: repeat(2, 1fr); }}
            .charts-row {{ grid-template-columns: 1fr; }}
        }}
    </style>
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
                        <tbody>
                            {top_files_rows}
                        </tbody>
                    </table>
                </div>
                <div class="card">
                    <div class="card-title">Top Callers</div>
                    <div class="card-subtitle">Functions that call the most other functions</div>
                    <table class="mini-table">
                        <thead><tr><th>Symbol</th><th style="width:50px;">Calls</th><th style="width:120px;"></th></tr></thead>
                        <tbody>
                            {top_callers_rows}
                        </tbody>
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
    
    <script>
    // ─── DATA ───
    const callGraphData = {call_graph_json};
    const fileDepsData = {file_deps_json};
    const typeCountsData = {type_counts_json};
    const langCountsData = {lang_counts_json};
    const typeColors = {type_colors_json};
    const langColors = {lang_colors_json};
    const searchData = {search_data_json};
    
    // ─── TABS ───
    function showTab(id, el) {{
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        document.getElementById(id).classList.add('active');
        if (el) el.classList.add('active');
        if (id === 'graph') initGraph();
        if (id === 'deps') initDeps();
    }}
    
    // ─── DONUT CHARTS ───
    function drawDonut(svgId, legendId, data, colorMap, defaultColor) {{
        const entries = Object.entries(data).sort((a,b) => b[1] - a[1]);
        const total = entries.reduce((s, e) => s + e[1], 0);
        if (!total) return;
        
        const svg = d3.select('#' + svgId);
        const w = 160, h = 160, r = 65, inner = 40;
        const g = svg.append('g').attr('transform', `translate(${{w/2}},${{h/2}})`);
        
        const pie = d3.pie().value(d => d[1]).sort(null).padAngle(0.02);
        const arc = d3.arc().innerRadius(inner).outerRadius(r);
        
        g.selectAll('path').data(pie(entries)).join('path')
            .attr('d', arc)
            .attr('fill', d => colorMap[d.data[0]] || defaultColor || '#475569')
            .attr('stroke', 'var(--bg2)')
            .attr('stroke-width', 2)
            .style('cursor', 'pointer')
            .on('mouseover', function() {{ d3.select(this).attr('opacity', 0.8); }})
            .on('mouseout', function() {{ d3.select(this).attr('opacity', 1); }});
        
        g.append('text').text(total).attr('text-anchor','middle').attr('dy','-0.1em').attr('fill','white').attr('font-size','22px').attr('font-weight','700');
        g.append('text').text('total').attr('text-anchor','middle').attr('dy','1.2em').attr('fill','var(--text3)').attr('font-size','11px');
        
        const legend = document.getElementById(legendId);
        legend.innerHTML = entries.slice(0, 8).map(([k, v]) => `
            <div class="chart-legend-item">
                <div class="chart-legend-dot" style="background:${{colorMap[k] || defaultColor || '#475569'}}"></div>
                <span>${{k}}</span>
                <span class="chart-legend-val">${{v}}</span>
            </div>
        `).join('');
    }}
    
    drawDonut('typeDonut', 'typeLegend', typeCountsData, typeColors, '#475569');
    drawDonut('langDonut', 'langLegend', langCountsData, langColors, '#475569');
    
    // ─── GLOBAL SEARCH ───
    function doGlobalSearch(q) {{
        const box = document.getElementById('searchResults');
        if (!q || q.length < 2) {{ box.style.display = 'none'; return; }}
        q = q.toLowerCase();
        const results = searchData.filter(s => s.name.toLowerCase().includes(q) || s.file.toLowerCase().includes(q)).slice(0, 15);
        if (!results.length) {{ box.innerHTML = '<div style="padding:14px;color:var(--text3);">No results</div>'; }}
        else {{
            box.innerHTML = results.map(s => `
                <div class="search-result-item" onclick="showTab('symbols',document.querySelectorAll('.nav-item')[1]);filterSymbols('${{s.name}}');document.getElementById('searchResults').style.display='none';">
                    <span class="badge badge-type">${{s.type}}</span>
                    <span style="color:var(--accent);font-weight:600;">${{s.name}}</span>
                    <span style="color:var(--text3);font-size:11px;margin-left:auto;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${{s.file}}:${{s.line}}</span>
                </div>
            `).join('');
        }}
        box.style.display = 'block';
    }}
    document.addEventListener('click', e => {{
        if (!e.target.closest('.search-wrapper')) document.getElementById('searchResults').style.display = 'none';
    }});
    
    // ─── SYMBOL FILTERS ───
    function filterSymbols(q) {{
        document.querySelectorAll('.symbol-card').forEach(c => {{
            const name = c.querySelector('.symbol-name').textContent.toLowerCase();
            const file = c.querySelector('.symbol-file')?.textContent?.toLowerCase() || '';
            c.style.display = (name.includes(q.toLowerCase()) || file.includes(q.toLowerCase())) ? '' : 'none';
        }});
    }}
    function filterByType(type, btn) {{
        document.querySelectorAll('#symbolFilterTabs .filter-tab').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.symbol-card').forEach(c => {{
            c.style.display = (type === 'all' || c.dataset.type === type) ? '' : 'none';
        }});
    }}
    function filterTree(q) {{
        document.querySelectorAll('.tree-item').forEach(i => {{
            i.style.display = i.textContent.toLowerCase().includes(q.toLowerCase()) ? 'flex' : 'none';
        }});
    }}
    function filterImports(type, btn) {{
        btn.parentElement.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        btn.closest('.card').querySelectorAll('.symbol-card').forEach(c => {{
            if (type === 'all') c.style.display = '';
            else c.style.display = (c.dataset.external === (type === 'external' ? 'True' : 'False')) ? '' : 'none';
        }});
    }}
    
    // ─── SYMBOL MODAL ───
    function showSymbolDetail(sym) {{
        document.getElementById('modalTitle').textContent = sym.name;
        let b = `<div class="modal-section"><div style="display:flex;gap:6px;flex-wrap:wrap;">`;
        b += `<span class="badge badge-type">${{sym.type}}</span>`;
        if (sym.framework) b += `<span class="badge badge-fw">${{sym.framework}}</span>`;
        if (sym.doc) b += `<span class="badge badge-doc">documented</span>`;
        b += `</div></div>`;
        b += `<div class="modal-section"><div class="modal-section-title">Location</div><div class="modal-code">${{sym.file}}:${{sym.line}}</div></div>`;
        if (sym.doc) b += `<div class="modal-section"><div class="modal-section-title">Documentation</div><p style="color:var(--text2);font-size:13px;line-height:1.6;">${{sym.doc}}</p></div>`;
        if (sym.params?.length) b += `<div class="modal-section"><div class="modal-section-title">Parameters</div><div class="modal-code">${{sym.params.join(', ')}}</div></div>`;
        if (sym.return_type) b += `<div class="modal-section"><div class="modal-section-title">Returns</div><div class="modal-code">${{sym.return_type}}</div></div>`;
        if (sym.calls?.length) {{
            b += `<div class="modal-section"><div class="modal-section-title">Calls (${{sym.calls.length}})</div><div style="display:flex;flex-wrap:wrap;gap:4px;">`;
            sym.calls.forEach(c => {{ b += `<span class="modal-tag" onclick="closeModal();highlightGraphNode('${{c}}')">${{c}}</span>`; }});
            b += `</div></div>`;
        }}
        // Find callers
        const callers = Object.entries(callGraphData).filter(([k,v]) => v.includes(sym.name)).map(([k]) => k);
        if (callers.length) {{
            b += `<div class="modal-section"><div class="modal-section-title">Called By (${{callers.length}})</div><div style="display:flex;flex-wrap:wrap;gap:4px;">`;
            callers.slice(0, 15).forEach(c => {{ b += `<span class="modal-tag" onclick="closeModal();highlightGraphNode('${{c}}')">${{c}}</span>`; }});
            b += `</div></div>`;
        }}
        if (sym.methods?.length) {{
            b += `<div class="modal-section"><div class="modal-section-title">Methods (${{sym.methods.length}})</div>`;
            sym.methods.forEach(m => {{ b += `<div style="padding:6px 0;border-bottom:1px solid var(--bg3);font-size:13px;font-family:monospace;">${{m.name}}(${{(m.params||[]).join(', ')}})</div>`; }});
            b += `</div>`;
        }}
        document.getElementById('modalBody').innerHTML = b;
        document.getElementById('symbolModal').classList.add('active');
    }}
    function closeModal() {{ document.getElementById('symbolModal').classList.remove('active'); }}
    document.getElementById('symbolModal').addEventListener('click', function(e) {{ if (e.target === this) closeModal(); }});
    
    // ─── CALL GRAPH (D3 Force) ───
    let graphSim, graphSvg, graphG, graphZoom, graphNodes, graphLinks, labelsVisible = true;
    let graphInited = false;
    
    function initGraph() {{
        if (graphInited) return;
        graphInited = true;
        
        const allIds = new Set(Object.keys(callGraphData));
        Object.values(callGraphData).forEach(ts => ts.forEach(t => allIds.add(t)));
        
        // Limit to nodes with connections
        const connected = new Set();
        Object.entries(callGraphData).forEach(([s, ts]) => {{
            if (ts.length) {{ connected.add(s); ts.forEach(t => connected.add(t)); }}
        }});
        const nodeIds = Array.from(connected).slice(0, 120);
        const nodeSet = new Set(nodeIds);
        
        const nodes = nodeIds.map(id => ({{
            id,
            calls: (callGraphData[id] || []).length,
            calledBy: Object.values(callGraphData).filter(v => v.includes(id)).length,
            isCaller: !!callGraphData[id]?.length
        }}));
        
        const links = [];
        Object.entries(callGraphData).forEach(([s, ts]) => {{
            ts.forEach(t => {{
                if (nodeSet.has(s) && nodeSet.has(t)) links.push({{ source: s, target: t }});
            }});
        }});
        
        document.getElementById('graphNodeCount').textContent = `${{nodes.length}} nodes · ${{links.length}} edges`;
        
        const container = document.getElementById('graphContainer');
        const W = container.clientWidth || 900, H = 600;
        
        graphSvg = d3.select('#graphContainer').append('svg').attr('width', W).attr('height', H);
        graphG = graphSvg.append('g');
        
        graphZoom = d3.zoom().scaleExtent([0.2, 5]).on('zoom', e => graphG.attr('transform', e.transform));
        graphSvg.call(graphZoom);
        
        // Arrow markers
        graphSvg.append('defs').append('marker').attr('id','arrowhead').attr('viewBox','0 -5 10 10').attr('refX',20).attr('refY',0).attr('markerWidth',6).attr('markerHeight',6).attr('orient','auto').append('path').attr('d','M0,-5L10,0L0,5').attr('fill','#475569');
        
        graphLinks = graphG.append('g').selectAll('line').data(links).join('line')
            .attr('class', 'link').attr('stroke', '#475569').attr('stroke-width', 1).attr('marker-end', 'url(#arrowhead)');
        
        const nodeG = graphG.append('g').selectAll('g').data(nodes).join('g')
            .attr('class', 'node').style('cursor', 'pointer');
        
        nodeG.append('circle')
            .attr('r', d => 5 + Math.min(d.calls + d.calledBy, 15))
            .attr('fill', d => d.isCaller ? 'var(--accent)' : 'var(--accent2)')
            .attr('stroke', '#fff').attr('stroke-width', 1.5);
        
        nodeG.append('text')
            .text(d => d.id.length > 18 ? d.id.substring(0, 18) + '…' : d.id)
            .attr('x', d => 8 + Math.min(d.calls + d.calledBy, 15))
            .attr('y', 4).attr('fill', 'var(--text)').attr('font-size', '11px')
            .attr('class', 'node-label');
        
        graphNodes = nodeG;
        
        // Hover tooltip
        const tooltip = document.getElementById('graphTooltip');
        nodeG.on('mouseover', (e, d) => {{
            tooltip.innerHTML = `<strong style="color:var(--accent)">${{d.id}}</strong><br><span style="color:var(--text3)">Calls: ${{d.calls}} · Called by: ${{d.calledBy}}</span>`;
            tooltip.style.display = 'block';
            tooltip.style.left = (e.offsetX + 12) + 'px';
            tooltip.style.top = (e.offsetY - 10) + 'px';
        }}).on('mouseout', () => {{ tooltip.style.display = 'none'; }});
        
        // Click to highlight
        nodeG.on('click', (e, d) => {{
            e.stopPropagation();
            highlightNode(d.id, nodes, links);
        }});
        
        graphSvg.on('click', () => {{ resetHighlight(); }});
        
        nodeG.call(d3.drag()
            .on('start', (e, d) => {{ if (!e.active) graphSim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
            .on('drag', (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
            .on('end', (e, d) => {{ if (!e.active) graphSim.alphaTarget(0); d.fx = null; d.fy = null; }}));
        
        graphSim = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(70))
            .force('charge', d3.forceManyBody().strength(-150))
            .force('center', d3.forceCenter(W / 2, H / 2))
            .force('collision', d3.forceCollide().radius(d => 10 + Math.min(d.calls + d.calledBy, 15)));
        
        graphSim.on('tick', () => {{
            graphLinks.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y);
            graphNodes.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
        }});
    }}
    
    function highlightNode(id, nodes, links) {{
        const calls = callGraphData[id] || [];
        const callers = Object.entries(callGraphData).filter(([k,v]) => v.includes(id)).map(([k]) => k);
        const related = new Set([id, ...calls, ...callers]);
        
        graphNodes.classed('dimmed', d => !related.has(d.id));
        graphLinks.classed('dimmed', d => d.source.id !== id && d.target.id !== id);
        graphLinks.classed('highlighted', d => d.source.id === id || d.target.id === id);
        
        const info = document.getElementById('graphInfo');
        info.classList.add('active');
        info.innerHTML = `
            <strong style="color:var(--accent);font-size:16px;">${{id}}</strong>
            <div style="margin-top:10px;display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div><div style="font-size:11px;color:var(--text3);text-transform:uppercase;margin-bottom:6px;">Calls (${{calls.length}})</div>
                    ${{calls.length ? calls.map(c => `<span class="modal-tag" onclick="highlightGraphNode('${{c}}')">${{c}}</span>`).join('') : '<span style="color:var(--text3)">none</span>'}}</div>
                <div><div style="font-size:11px;color:var(--text3);text-transform:uppercase;margin-bottom:6px;">Called By (${{callers.length}})</div>
                    ${{callers.length ? callers.slice(0,10).map(c => `<span class="modal-tag" onclick="highlightGraphNode('${{c}}')">${{c}}</span>`).join('') : '<span style="color:var(--text3)">none</span>'}}</div>
            </div>`;
    }}
    
    function resetHighlight() {{
        if (!graphNodes) return;
        graphNodes.classed('dimmed', false);
        graphLinks.classed('dimmed', false).classed('highlighted', false);
        document.getElementById('graphInfo').classList.remove('active');
    }}
    
    function highlightGraphNode(name) {{
        showTab('graph', document.querySelectorAll('.nav-item')[2]);
        setTimeout(() => {{
            const nd = graphNodes?.data()?.find(d => d.id === name);
            if (nd) highlightNode(name, graphNodes.data(), graphLinks.data());
        }}, 100);
    }}
    
    function searchGraphNode(q) {{
        if (!graphNodes) return;
        if (!q) {{ resetHighlight(); return; }}
        q = q.toLowerCase();
        graphNodes.classed('dimmed', d => !d.id.toLowerCase().includes(q));
        graphLinks.classed('dimmed', true);
    }}
    
    function resetGraph() {{ resetHighlight(); if (graphSvg) graphSvg.transition().call(graphZoom.transform, d3.zoomIdentity); }}
    function zoomIn() {{ if (graphSvg) graphSvg.transition().call(graphZoom.scaleBy, 1.4); }}
    function zoomOut() {{ if (graphSvg) graphSvg.transition().call(graphZoom.scaleBy, 0.7); }}
    function toggleLabels() {{
        labelsVisible = !labelsVisible;
        d3.selectAll('.node-label').style('display', labelsVisible ? 'block' : 'none');
        document.getElementById('toggleLabels').textContent = labelsVisible ? 'Hide Labels' : 'Show Labels';
    }}
    
    // ─── FILE DEPS GRAPH ───
    let depsInited = false;
    function initDeps() {{
        if (depsInited) return;
        depsInited = true;
        
        const allFiles = new Set();
        Object.entries(fileDepsData).forEach(([f, deps]) => {{
            allFiles.add(f); deps.forEach(d => allFiles.add(d));
        }});
        const fileArr = Array.from(allFiles).slice(0, 80);
        const fileSet = new Set(fileArr);
        const nodes = fileArr.map(f => ({{ id: f, short: f.split('/').pop() }}));
        const links = [];
        Object.entries(fileDepsData).forEach(([s, deps]) => {{
            deps.forEach(t => {{ if (fileSet.has(s) && fileSet.has(t)) links.push({{ source: s, target: t }}); }});
        }});
        
        const container = document.getElementById('depsContainer');
        const W = container.clientWidth || 900, H = 500;
        const svg = d3.select('#depsContainer').append('svg').attr('width', W).attr('height', H);
        const g = svg.append('g');
        
        const zoom = d3.zoom().scaleExtent([0.2, 4]).on('zoom', e => g.attr('transform', e.transform));
        svg.call(zoom);
        
        svg.append('defs').append('marker').attr('id','depArrow').attr('viewBox','0 -5 10 10').attr('refX',14).attr('refY',0).attr('markerWidth',5).attr('markerHeight',5).attr('orient','auto').append('path').attr('d','M0,-5L10,0L0,5').attr('fill','var(--green)');
        
        const link = g.append('g').selectAll('line').data(links).join('line')
            .attr('stroke', 'var(--green)').attr('stroke-opacity', 0.3).attr('stroke-width', 1).attr('marker-end', 'url(#depArrow)');
        
        const node = g.append('g').selectAll('g').data(nodes).join('g').style('cursor','pointer');
        node.append('circle').attr('r', 6).attr('fill', 'var(--green)').attr('stroke', '#fff').attr('stroke-width', 1);
        node.append('text').text(d => d.short.length > 20 ? d.short.substring(0,20)+'…' : d.short).attr('x',10).attr('y',4).attr('fill','var(--text2)').attr('font-size','10px');
        
        node.on('click', (e, d) => {{
            e.stopPropagation();
            const imports = fileDepsData[d.id] || [];
            const importedBy = Object.entries(fileDepsData).filter(([k,v]) => v.includes(d.id)).map(([k]) => k);
            const related = new Set([d.id, ...imports, ...importedBy]);
            node.selectAll('circle').attr('opacity', dd => related.has(dd.id) ? 1 : 0.1);
            node.selectAll('text').attr('opacity', dd => related.has(dd.id) ? 1 : 0.1);
            link.attr('stroke-opacity', dd => dd.source.id === d.id || dd.target.id === d.id ? 0.8 : 0.05);
            
            const info = document.getElementById('depsInfo');
            info.classList.add('active');
            info.innerHTML = `<strong style="color:var(--green)">${{d.id}}</strong>
                <div style="margin-top:10px;display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div><div style="font-size:11px;color:var(--text3);text-transform:uppercase;margin-bottom:6px;">Imports (${{imports.length}})</div>${{imports.map(f=>`<div style="font-size:12px;color:var(--text2);padding:2px 0;">${{f}}</div>`).join('')||'<span style="color:var(--text3)">none</span>'}}</div>
                <div><div style="font-size:11px;color:var(--text3);text-transform:uppercase;margin-bottom:6px;">Imported By (${{importedBy.length}})</div>${{importedBy.map(f=>`<div style="font-size:12px;color:var(--text2);padding:2px 0;">${{f}}</div>`).join('')||'<span style="color:var(--text3)">none</span>'}}</div></div>`;
        }});
        svg.on('click', () => {{
            node.selectAll('circle').attr('opacity', 1); node.selectAll('text').attr('opacity', 1);
            link.attr('stroke-opacity', 0.3);
            document.getElementById('depsInfo').classList.remove('active');
        }});
        
        node.call(d3.drag()
            .on('start', (e, d) => {{ if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
            .on('drag', (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
            .on('end', (e, d) => {{ if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }}));
        
        const sim = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(60))
            .force('charge', d3.forceManyBody().strength(-100))
            .force('center', d3.forceCenter(W/2, H/2));
        
        sim.on('tick', () => {{
            link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y).attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
            node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
        }});
    }}
    
    function searchDepsNode(q) {{
        // simple text-based highlight
    }}
    function resetDeps() {{
        const svg = d3.select('#depsContainer svg');
        if (svg.node()) svg.transition().call(d3.zoom().transform, d3.zoomIdentity);
    }}
    </script>
</body>
</html>"""
    
    output_path.write_text(html, encoding="utf-8")


def generate_tree_html(tree: dict, depth: int) -> str:
    """Generate HTML for file tree."""
    html = ""
    for name, content in sorted(tree.items()):
        if isinstance(content, dict):
            html += f'<div class="tree-item folder" style="padding-left: {depth * 20}px;">📁 {name}/</div>'
            html += generate_tree_html(content, depth + 1)
        else:
            sym_count = len(content) if isinstance(content, list) else 0
            html += f'<div class="tree-item file" style="padding-left: {depth * 20}px;">📄 {name} <span style="color: #64748b;">({sym_count})</span></div>'
    return html


def generate_symbols_html(symbols: list) -> str:
    """Generate HTML for symbol cards."""
    html = ""
    for sym in symbols:
        params_str = ", ".join(sym.get("params", [])[:3])
        if len(sym.get("params", [])) > 3:
            params_str += "..."
        
        fw = sym.get("framework", "")
        fw_html = f'<span class="badge badge-fw">{fw}</span>' if fw else ""
        doc = sym.get("doc", "")
        doc_html = '<span class="badge badge-doc">doc</span>' if doc else ""
        
        # Escape the JSON for safe embedding in onclick
        sym_json = json.dumps(sym).replace("'", "&#39;").replace('"', "&quot;")
        
        html += f"""<div class="symbol-card" data-type="{sym.get('type', 'function')}" onclick='showSymbolDetail({json.dumps(sym)})'>
            <div class="symbol-name">{sym.get('name', 'unknown')}</div>
            <div class="symbol-meta"><span class="badge badge-type">{sym.get('type', 'function')}</span>{fw_html}{doc_html}</div>
            <div class="symbol-file">{sym.get('file', 'unknown')}:{sym.get('line', 0)}</div>
            {f'<div class="symbol-params">{params_str}</div>' if params_str else ''}
        </div>"""
    return html


def generate_imports_html(imports: list) -> str:
    """Generate HTML for import cards."""
    html = ""
    for imp in imports:
        module = imp.get("module", "unknown")
        imported = imp.get("imported", [])
        file = imp.get("file", "unknown")
        
        is_external = not module.startswith(".")
        
        html += f"""<div class="symbol-card" data-external="{is_external}">
            <div class="symbol-name">{module}</div>
            <span class="symbol-type">{'external' if is_external else 'internal'}</span>
            <div class="symbol-file">{file}</div>
            <div class="symbol-params">{', '.join(imported) if imported else 'default'}</div>
        </div>"""
    return html


def generate_exports_html(exports: list) -> str:
    """Generate HTML for export cards."""
    html = ""
    for exp in exports:
        name = exp.get("name", "unknown")
        exp_type = exp.get("type", "unknown")
        file = exp.get("file", "unknown")
        
        html += f"""<div class="symbol-card">
            <div class="symbol-name">{name}</div>
            <span class="symbol-type">{exp_type}</span>
            <div class="symbol-file">{file}</div>
        </div>"""
    return html


def generate_routes_html(routes: list) -> str:
    """Generate HTML for API route cards."""
    html = ""
    for route in routes:
        method = route.get("method", "GET")
        path = route.get("path", "/")
        framework = route.get("framework", "unknown")
        file = route.get("file", "unknown")
        
        method_colors = {"GET": "#10b981", "POST": "#3b82f6", "PUT": "#f59e0b", "DELETE": "#ef4444", "PATCH": "#8b5cf6"}
        color = method_colors.get(method, "#6b7280")
        
        html += f"""<div class="symbol-card">
            <div class="symbol-name" style="display: flex; align-items: center; gap: 8px;">
                <span style="background: {color}; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">{method}</span>
                {path}
            </div>
            <span class="symbol-type">{framework}</span>
            <div class="symbol-file">{file}</div>
        </div>"""
    return html


def generate_entities_html(entities: list) -> str:
    """Generate HTML for entity cards."""
    html = ""
    for ent in entities:
        name = ent.get("name", "unknown")
        ent_type = ent.get("type", "unknown")
        fields = ent.get("fields", [])
        file = ent.get("file", "unknown")
        
        html += f"""<div class="symbol-card">
            <div class="symbol-name">{name}</div>
            <span class="symbol-type">{ent_type}</span>
            <div class="symbol-file">{file}</div>
            <div class="symbol-params">{', '.join(fields[:5])}{'...' if len(fields) > 5 else ''}</div>
        </div>"""
    return html
