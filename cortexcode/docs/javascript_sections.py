"""Named JavaScript template sections for the interactive dashboard."""

DATA_AND_TABS_SECTION = """
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
"""

DONUT_SECTION = """
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
"""

SEARCH_AND_FILTER_SECTION = """
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
"""

MODAL_SECTION = """
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
"""

CALL_GRAPH_SECTION = """
// ─── CALL GRAPH (D3 Force) ───
let graphSim, graphSvg, graphG, graphZoom, graphNodes, graphLinks, labelsVisible = true;
let graphInited = false;

function initGraph() {{
    if (graphInited) return;
    graphInited = true;
    
    const allIds = new Set(Object.keys(callGraphData));
    Object.values(callGraphData).forEach(ts => ts.forEach(t => allIds.add(t)));
    
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
    
    graphSvg.append('defs').append('marker').attr('id','arrowhead').attr('viewBox','0 -5 10 10').attr('refX',20).attr('refY',0).attr('markerWidth',6).attr('markerHeight',6).attr('orient','auto').append('path').attr('d','M0,-5L10,0L0,5').attr('fill','var(--bg4)');
    
    graphLinks = graphG.append('g').selectAll('line').data(links).join('line')
        .attr('class', 'link').attr('stroke', 'var(--bg4)').attr('stroke-width', 1).attr('marker-end', 'url(#arrowhead)');
    
    const nodeG = graphG.append('g').selectAll('g').data(nodes).join('g')
        .attr('class', 'node').style('cursor', 'pointer');
    
    nodeG.append('circle')
        .attr('r', d => 5 + Math.min(d.calls + d.calledBy, 15))
        .attr('fill', d => d.isCaller ? 'var(--accent)' : 'var(--accent2)')
        .attr('stroke', '#fff').attr('stroke-width', 1.5);
    
    nodeG.append('text')
        .text(d => d.id.length > 16 ? d.id.substring(0, 16) + '…' : d.id)
        .attr('x', d => 8 + Math.min(d.calls + d.calledBy, 15))
        .attr('y', 4).attr('font-size', '11px')
        .attr('class', 'node-label');
    
    graphNodes = nodeG;
    
    const tooltip = document.getElementById('graphTooltip');
    nodeG.on('mouseover', (e, d) => {{
        tooltip.innerHTML = `<strong style="color:var(--accent)">${{d.id}}</strong><br><span style="color:var(--text3)">Calls: ${{d.calls}} · Called by: ${{d.calledBy}}</span>`;
        tooltip.style.display = 'block';
        tooltip.style.left = (e.offsetX + 12) + 'px';
        tooltip.style.top = (e.offsetY - 10) + 'px';
    }}).on('mouseout', () => {{ tooltip.style.display = 'none'; }});
    
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
        .force('collision', d3.forceCollide().radius(d => 20 + Math.min(d.calls + d.calledBy, 15)));
    
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
"""

FILE_DEPS_SECTION = """
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

function searchDepsNode(q) {{}}
function resetDeps() {{
    const svg = d3.select('#depsContainer svg');
    if (svg.node()) svg.transition().call(d3.zoom().transform, d3.zoomIdentity);
}}
"""


def build_dashboard_js_template() -> str:
    """Build the full interactive dashboard JavaScript template."""
    return "\n\n".join([
        DATA_AND_TABS_SECTION.strip(),
        DONUT_SECTION.strip(),
        SEARCH_AND_FILTER_SECTION.strip(),
        MODAL_SECTION.strip(),
        CALL_GRAPH_SECTION.strip(),
        FILE_DEPS_SECTION.strip(),
    ]) + "\n"
