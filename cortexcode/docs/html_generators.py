"""HTML fragment generators for documentation."""

import json


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
