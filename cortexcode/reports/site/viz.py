"""Interactive visualization generator - premium dark mode with glassmorphism."""

import json
from pathlib import Path
from typing import Any


def generate_viz_html(index: dict[str, Any], output_path: Path) -> None:
    """Generate a premium interactive visualization HTML."""
    
    files = index.get("files", {})
    call_graph = index.get("call_graph", {})
    project_root = index.get("project_root", ".")
    project_name = Path(project_root).name
    
    nodes = []
    links = []
    node_set = set()
    
    for file_path, data in files.items():
        symbols = data.get("symbols", []) if isinstance(data, dict) else data
        for sym in symbols:
            name = sym.get("name", "")
            sym_type = sym.get("type", "function")
            line = sym.get("line", 0)
            
            if name and name not in node_set:
                node_set.add(name)
                nodes.append({
                    "id": name,
                    "label": name,
                    "type": sym_type,
                    "file": file_path,
                    "line": line,
                    "params": sym.get("params", []),
                    "class": sym.get("class", ""),
                })
            
            calls = sym.get("calls", [])
            for callee in calls:
                if callee not in node_set:
                    node_set.add(callee)
                    nodes.append({"id": callee, "label": callee, "type": "function", "file": "", "line": 0})
                links.append({"source": name, "target": callee})
    
    viz_data = {
        "project": project_name,
        "nodes": nodes[:500],
        "links": links[:1000],
        "stats": {
            "files": len(files),
            "symbols": len(nodes),
            "edges": len(links),
        }
    }
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} — Code Graph</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        :root {{
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-tertiary: #1a1a25;
            --bg-card: rgba(26, 26, 37, 0.7);
            --text-primary: #f0f0f5;
            --text-secondary: #8888a0;
            --text-muted: #555566;
            --accent-cyan: #00d4ff;
            --accent-purple: #a855f7;
            --accent-green: #10b981;
            --accent-orange: #f97316;
            --accent-pink: #ec4899;
            --border-glass: rgba(255, 255, 255, 0.08);
            --shadow-glass: 0 8px 32px rgba(0, 0, 0, 0.4);
            --blur: 12px;
        }}
        
        body {{
            font-family: 'Outfit', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow: hidden;
        }}
        
        .app {{
            display: flex;
            height: 100vh;
        }}
        
        .sidebar {{
            width: 280px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-glass);
            padding: 24px;
            display: flex;
            flex-direction: column;
            backdrop-filter: blur(var(--blur));
        }}
        
        .logo {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 32px;
        }}
        
        .logo-icon {{
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 18px;
            color: white;
        }}
        
        .logo-text {{
            font-size: 20px;
            font-weight: 600;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 24px;
        }}
        
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-glass);
            border-radius: 12px;
            padding: 16px;
            backdrop-filter: blur(var(--blur));
        }}
        
        .stat-value {{
            font-size: 28px;
            font-weight: 700;
            color: var(--accent-cyan);
            font-family: 'JetBrains Mono', monospace;
        }}
        
        .stat-label {{
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 4px;
        }}
        
        .search-box {{
            background: var(--bg-tertiary);
            border: 1px solid var(--border-glass);
            border-radius: 10px;
            padding: 12px 16px;
            color: var(--text-primary);
            font-size: 14px;
            width: 100%;
            margin-bottom: 16px;
            font-family: 'Outfit', sans-serif;
        }}
        
        .search-box:focus {{
            outline: none;
            border-color: var(--accent-cyan);
        }}
        
        .search-box::placeholder {{
            color: var(--text-muted);
        }}
        
        .nav-section {{
            margin-bottom: 16px;
        }}
        
        .nav-title {{
            font-size: 10px;
            text-transform: uppercase;
            color: var(--text-muted);
            letter-spacing: 1px;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        
        .nav-item {{
            padding: 10px 12px;
            border-radius: 8px;
            cursor: pointer;
            color: var(--text-secondary);
            font-size: 13px;
            transition: all 0.15s;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .nav-item:hover {{
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }}
        
        .nav-item.active {{
            background: linear-gradient(135deg, rgba(0, 212, 255, 0.15), rgba(168, 85, 247, 0.15));
            color: var(--accent-cyan);
            border: 1px solid rgba(0, 212, 255, 0.3);
        }}
        
        .main {{
            flex: 1;
            position: relative;
            background: 
                radial-gradient(ellipse at 20% 20%, rgba(0, 212, 255, 0.05) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(168, 85, 247, 0.05) 0%, transparent 50%),
                var(--bg-primary);
        }}
        
        .graph-container {{
            width: 100%;
            height: 100%;
        }}
        
        .controls {{
            position: absolute;
            top: 20px;
            right: 20px;
            display: flex;
            gap: 8px;
            z-index: 10;
        }}
        
        .control-btn {{
            background: var(--bg-card);
            border: 1px solid var(--border-glass);
            border-radius: 8px;
            padding: 10px 16px;
            color: var(--text-secondary);
            font-size: 13px;
            cursor: pointer;
            backdrop-filter: blur(var(--blur));
            transition: all 0.15s;
            font-family: 'Outfit', sans-serif;
        }}
        
        .control-btn:hover {{
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border-color: var(--accent-cyan);
        }}
        
        .node {{
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .node:hover {{
            filter: brightness(1.3);
        }}
        
        .node-label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            fill: var(--text-secondary);
            pointer-events: none;
            text-shadow: 0 0 4px var(--bg-primary), 0 0 8px var(--bg-primary);
        }}
        
        .node-label-bg {{
            fill: var(--bg-primary);
            opacity: 0.75;
            rx: 3;
        }}
        
        .link {{
            stroke: var(--border-glass);
            stroke-width: 1;
            fill: none;
        }}
        
        .detail-panel {{
            position: absolute;
            top: 20px;
            right: 20px;
            width: 320px;
            background: var(--bg-card);
            border: 1px solid var(--border-glass);
            border-radius: 16px;
            padding: 20px;
            backdrop-filter: blur(var(--blur));
            box-shadow: var(--shadow-glass);
            display: none;
            z-index: 20;
        }}
        
        .detail-panel.visible {{
            display: block;
        }}
        
        .detail-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
        }}
        
        .detail-name {{
            font-size: 18px;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
            color: var(--accent-cyan);
        }}
        
        .detail-type {{
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 20px;
            background: rgba(168, 85, 247, 0.2);
            color: var(--accent-purple);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .detail-close {{
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 20px;
            padding: 0;
            line-height: 1;
        }}
        
        .detail-close:hover {{
            color: var(--text-primary);
        }}
        
        .detail-row {{
            display: flex;
            margin-bottom: 12px;
        }}
        
        .detail-label {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            width: 60px;
            flex-shrink: 0;
        }}
        
        .detail-value {{
            font-size: 13px;
            color: var(--text-secondary);
            font-family: 'JetBrains Mono', monospace;
            word-break: break-all;
        }}
        
        .detail-section {{
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--border-glass);
        }}
        
        .detail-section-title {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        
        .detail-link {{
            display: block;
            padding: 8px 12px;
            background: var(--bg-tertiary);
            border-radius: 8px;
            margin-bottom: 6px;
            font-size: 12px;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.15s;
            font-family: 'JetBrains Mono', monospace;
        }}
        
        .detail-link:hover {{
            background: rgba(0, 212, 255, 0.1);
            color: var(--accent-cyan);
        }}
        
        .legend {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            display: flex;
            gap: 16px;
            background: var(--bg-card);
            border: 1px solid var(--border-glass);
            border-radius: 10px;
            padding: 12px 16px;
            backdrop-filter: blur(var(--blur));
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: var(--text-secondary);
        }}
        
        .legend-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }}
        
        .tooltip {{
            position: absolute;
            background: var(--bg-card);
            border: 1px solid var(--border-glass);
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 12px;
            color: var(--text-primary);
            pointer-events: none;
            backdrop-filter: blur(var(--blur));
            z-index: 100;
            display: none;
        }}
    </style>
</head>
<body>
    <div class="app">
        <div class="sidebar">
            <div class="logo">
                <div class="logo-icon">C</div>
                <div class="logo-text">CortexCode</div>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{viz_data['stats']['files']}</div>
                    <div class="stat-label">Files</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{viz_data['stats']['symbols']}</div>
                    <div class="stat-label">Symbols</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{viz_data['stats']['edges']}</div>
                    <div class="stat-label">Edges</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len([n for n in viz_data['nodes'] if n['type'] == 'class'])}</div>
                    <div class="stat-label">Classes</div>
                </div>
            </div>
            
            <input type="text" class="search-box" placeholder="Search symbols..." id="searchInput" oninput="filterNodes(this.value)">
            
            <div class="nav-section">
                <div class="nav-title">Layout</div>
                <div class="nav-item active" onclick="setLayout('force', this)">⚡ Force Directed</div>
                <div class="nav-item" onclick="setLayout('hierarchical', this)">🌳 Hierarchical</div>
            </div>
            
            <div class="nav-section">
                <div class="nav-title">Filter</div>
                <div class="nav-item" onclick="filterByType('all')">All</div>
                <div class="nav-item" onclick="filterByType('class')">Classes</div>
                <div class="nav-item" onclick="filterByType('function')">Functions</div>
                <div class="nav-item" onclick="filterByType('method')">Methods</div>
            </div>
        </div>
        
        <div class="main">
            <div class="controls">
                <button class="control-btn" onclick="resetView()">Reset</button>
                <button class="control-btn" onclick="zoomIn()">Zoom +</button>
                <button class="control-btn" onclick="zoomOut()">Zoom −</button>
                <button class="control-btn" onclick="toggleLabels()">Labels</button>
            </div>
            
            <svg class="graph-container" id="graph"></svg>
            
            <div class="detail-panel" id="detailPanel">
                <div class="detail-header">
                    <div>
                        <div class="detail-name" id="detailName">function_name</div>
                        <div class="detail-type" id="detailType">function</div>
                    </div>
                    <button class="detail-close" onclick="closeDetail()">×</button>
                </div>
                <div class="detail-row">
                    <div class="detail-label">File</div>
                    <div class="detail-value" id="detailFile">src/main.py</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Line</div>
                    <div class="detail-value" id="detailLine">42</div>
                </div>
                <div class="detail-section" id="callsSection">
                    <div class="detail-section-title">Calls</div>
                    <div id="detailCalls"></div>
                </div>
                <div class="detail-section" id="callersSection">
                    <div class="detail-section-title">Called By</div>
                    <div id="detailCallers"></div>
                </div>
            </div>
            
            <div class="legend">
                <div class="legend-item"><div class="legend-dot" style="background: #00d4ff;"></div>Function</div>
                <div class="legend-item"><div class="legend-dot" style="background: #a855f7;"></div>Class</div>
                <div class="legend-item"><div class="legend-dot" style="background: #10b981;"></div>Method</div>
                <div class="legend-item"><div class="legend-dot" style="background: #f97316;"></div>Interface</div>
            </div>
            
            <div class="tooltip" id="tooltip"></div>
        </div>
    </div>
    
    <script>
        const data = {json.dumps(viz_data, indent=2)};
        
        const typeColors = {{
            'function': '#00d4ff',
            'class': '#a855f7',
            'method': '#10b981',
            'interface': '#f97316',
            'default': '#8888a0'
        }};
        
        let currentLayout = 'force';
        let showLabels = true;
        let simulation, svg, g, zoom;
        
        function init() {{
            const container = document.getElementById('graph');
            const width = container.clientWidth;
            const height = container.clientHeight;
            
            svg = d3.select('#graph')
                .attr('width', width)
                .attr('height', height);
            
            g = svg.append('g');
            
            zoom = d3.zoom()
                .scaleExtent([0.1, 4])
                .on('zoom', (event) => {{
                    g.attr('transform', event.transform);
                }});
            
            svg.call(zoom);
            
            renderGraph();
        }}
        
        function renderGraph() {{
            g.selectAll('*').remove();
            
            const nodes = data.nodes.map(d => ({{...d}}));
            const links = data.links.map(d => ({{...d}}));
            
            const nodeMap = new Map(nodes.map(n => [n.id, n]));
            const validLinks = links.filter(l => nodeMap.has(l.source) && nodeMap.has(l.target));
            
            if (currentLayout === 'force') {{
                renderForce(nodes, validLinks);
            }} else {{
                renderHierarchical(nodes, validLinks);
            }}
        }}
        
        function renderForce(nodes, links) {{
            simulation = d3.forceSimulation(nodes)
                .force('link', d3.forceLink(links).id(d => d.id).distance(80))
                .force('charge', d3.forceManyBody().strength(-200))
                .force('center', d3.forceCenter(window.innerWidth * 0.6 / 2, window.innerHeight / 2))
                .force('collision', d3.forceCollide().radius(d => d.type === 'class' ? 50 : 40));
            
            const link = g.append('g')
                .selectAll('line')
                .data(links)
                .join('line')
                .attr('class', 'link')
                .attr('stroke-opacity', 0.4);
            
            const node = g.append('g')
                .selectAll('g')
                .data(nodes)
                .join('g')
                .attr('class', 'node')
                .call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended))
                .on('click', (event, d) => showDetail(d))
                .on('mouseover', (event, d) => showTooltip(event, d))
                .on('mouseout', hideTooltip);
            
            node.append('circle')
                .attr('r', d => d.type === 'class' ? 12 : 8)
                .attr('fill', d => typeColors[d.type] || typeColors.default)
                .attr('stroke', 'rgba(255,255,255,0.2)')
                .attr('stroke-width', 2);
            
            if (showLabels) {{
                node.append('rect')
                    .attr('class', 'node-label-bg')
                    .attr('x', 14)
                    .attr('y', -6)
                    .attr('width', d => Math.min(d.label.length, 16) * 6.5 + 8)
                    .attr('height', 14);
                node.append('text')
                    .attr('class', 'node-label')
                    .attr('dx', 18)
                    .attr('dy', 4)
                    .text(d => d.label.length > 16 ? d.label.substring(0, 16) + '…' : d.label);
            }}
            
            simulation.on('tick', () => {{
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
                
                node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
            }});
        }}
        
        function renderHierarchical(nodes, links) {{
            const nodeMap = new Map(nodes.map(n => [n.id, n]));
            const levels = new Map();
            
            nodes.forEach(n => {{
                const callers = links.filter(l => l.target === n.id).map(l => l.source);
                if (callers.length === 0) {{
                    levels.set(n.id, 0);
                }}
            }});
            
            let changed = true;
            while (changed) {{
                changed = false;
                nodes.forEach(n => {{
                    if (!levels.has(n.id)) {{
                        const callers = links.filter(l => l.target === n.id).map(l => l.source);
                        const maxLevel = Math.max(...callers.map(c => levels.get(c) ?? 0), -1);
                        if (callers.every(c => levels.has(c))) {{
                            levels.set(n.id, maxLevel + 1);
                            changed = true;
                        }}
                    }}
                }});
            }}
            
            nodes.forEach(n => {{
                if (!levels.has(n.id)) levels.set(n.id, 0);
            }});
            
            const levelGroups = new Map();
            nodes.forEach(n => {{
                const level = levels.get(n.id) || 0;
                if (!levelGroups.has(level)) levelGroups.set(level, []);
                levelGroups.get(level).push(n);
            }});
            
            const width = window.innerWidth * 0.8;
            const height = window.innerHeight * 0.8;
            const levelWidth = width / (levelGroups.size + 1);
            
            let yOffset = 0;
            levelGroups.forEach((group, level) => {{
                const yStep = height / (group.length + 1);
                group.forEach((n, i) => {{
                    n.x = (level + 1) * levelWidth;
                    n.y = (i + 1) * yStep;
                }});
            }});
            
            const link = g.append('g')
                .selectAll('line')
                .data(links)
                .join('line')
                .attr('class', 'link')
                .attr('stroke-opacity', 0.4)
                .attr('x1', d => nodeMap.get(d.source)?.x || 0)
                .attr('y1', d => nodeMap.get(d.source)?.y || 0)
                .attr('x2', d => nodeMap.get(d.target)?.x || 0)
                .attr('y2', d => nodeMap.get(d.target)?.y || 0);
            
            const node = g.append('g')
                .selectAll('g')
                .data(nodes)
                .join('g')
                .attr('class', 'node')
                .attr('transform', d => `translate(${{d.x}},${{d.y}})`)
                .on('click', (event, d) => showDetail(d))
                .on('mouseover', (event, d) => showTooltip(event, d))
                .on('mouseout', hideTooltip);
            
            node.append('circle')
                .attr('r', d => d.type === 'class' ? 12 : 8)
                .attr('fill', d => typeColors[d.type] || typeColors.default)
                .attr('stroke', 'rgba(255,255,255,0.2)')
                .attr('stroke-width', 2);
            
            if (showLabels) {{
                node.append('rect')
                    .attr('class', 'node-label-bg')
                    .attr('x', 14)
                    .attr('y', -6)
                    .attr('width', d => Math.min(d.label.length, 16) * 6.5 + 8)
                    .attr('height', 14);
                node.append('text')
                    .attr('class', 'node-label')
                    .attr('dx', 18)
                    .attr('dy', 4)
                    .text(d => d.label.length > 16 ? d.label.substring(0, 16) + '…' : d.label);
            }}
        }}
        
        function showDetail(d) {{
            document.getElementById('detailName').textContent = d.label;
            document.getElementById('detailType').textContent = d.type;
            document.getElementById('detailFile').textContent = d.file || 'N/A';
            document.getElementById('detailLine').textContent = d.line || 'N/A';
            
            const calls = data.links.filter(l => l.source === d.id).map(l => l.target);
            const callers = data.links.filter(l => l.target === d.id).map(l => l.source);
            
            document.getElementById('detailCalls').innerHTML = calls.length 
                ? calls.slice(0, 10).map(c => `<div class="detail-link">${{c}}</div>`).join('')
                : '<div style="color: var(--text-muted); font-size: 12px;">None</div>';
            
            document.getElementById('detailCallers').innerHTML = callers.length
                ? callers.slice(0, 10).map(c => `<div class="detail-link">${{c}}</div>`).join('')
                : '<div style="color: var(--text-muted); font-size: 12px;">None</div>';
            
            document.getElementById('detailPanel').classList.add('visible');
        }}
        
        function closeDetail() {{
            document.getElementById('detailPanel').classList.remove('visible');
        }}
        
        function showTooltip(event, d) {{
            const tooltip = document.getElementById('tooltip');
            tooltip.textContent = `${{d.label}} (${{d.type}}) - ${{d.file}}:${{d.line}}`;
            tooltip.style.left = event.pageX + 10 + 'px';
            tooltip.style.top = event.pageY + 10 + 'px';
            tooltip.style.display = 'block';
        }}
        
        function hideTooltip() {{
            document.getElementById('tooltip').style.display = 'none';
        }}
        
        function setLayout(layout, btn) {{
            currentLayout = layout;
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            btn.classList.add('active');
            renderGraph();
        }}
        
        function filterNodes(query) {{
            if (!query) {{
                g.selectAll('.node').style('opacity', 1);
                g.selectAll('.link').style('opacity', 0.4);
                return;
            }}
            const q = query.toLowerCase();
            g.selectAll('.node').style('opacity', d => 
                d.label.toLowerCase().includes(q) ? 1 : 0.2
            );
        }}
        
        function filterByType(type) {{
            if (type === 'all') {{
                g.selectAll('.node').style('display', 'block');
                return;
            }}
            g.selectAll('.node').style('display', d => 
                d.type === type ? 'block' : 'none'
            );
        }}
        
        function resetView() {{
            svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
        }}
        
        function zoomIn() {{
            svg.transition().duration(300).call(zoom.scaleBy, 1.3);
        }}
        
        function zoomOut() {{
            svg.transition().duration(300).call(zoom.scaleBy, 0.7);
        }}
        
        function toggleLabels() {{
            showLabels = !showLabels;
            renderGraph();
        }}
        
        function dragstarted(event) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }}
        
        function dragged(event) {{
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }}
        
        function dragended(event) {{
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }}
        
        window.addEventListener('resize', () => {{
            const container = document.getElementById('graph');
            svg.attr('width', container.clientWidth).attr('height', container.clientHeight);
        }});
        
        init();
    </script>
</body>
</html>"""
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
