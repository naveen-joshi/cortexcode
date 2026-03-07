"""Generate a multi-page CodeWiki-style documentation site."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from cortexcode.knowledge.models import KnowledgePack, ConceptEntry
from cortexcode.knowledge.usage import aggregate_usage


def _css() -> str:
    """Return the CSS for the wiki site."""
    return """
:root {
    --bg: #0d1117; --bg2: #161b22; --bg3: #21262d;
    --text: #e6edf3; --text2: #8b949e; --text3: #484f58;
    --accent: #58a6ff; --accent2: #3fb950; --accent3: #d2a8ff;
    --border: #30363d; --hover: #1f2937;
    --code-bg: #1a1f2b; --card-bg: #161b22;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
       background: var(--bg); color: var(--text); display: flex; min-height: 100vh; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Sidebar */
.sidebar { width: 260px; background: var(--bg2); border-right: 1px solid var(--border);
           position: fixed; top: 0; left: 0; bottom: 0; overflow-y: auto; z-index: 10; }
.sidebar-header { padding: 20px; border-bottom: 1px solid var(--border); }
.sidebar-header h1 { font-size: 18px; color: var(--accent); }
.sidebar-header p { font-size: 12px; color: var(--text2); margin-top: 4px; }
.nav-section { padding: 12px 0; }
.nav-title { padding: 4px 20px; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
             color: var(--text3); font-weight: 600; }
.nav-item { padding: 6px 20px; font-size: 14px; color: var(--text2); cursor: pointer;
            display: block; transition: all 0.15s; }
.nav-item:hover { background: var(--hover); color: var(--text); text-decoration: none; }
.nav-item.active { color: var(--accent); background: rgba(88,166,255,0.1);
                   border-left: 3px solid var(--accent); padding-left: 17px; }

/* Main */
.main { margin-left: 260px; flex: 1; min-height: 100vh; }
.topbar { padding: 16px 32px; border-bottom: 1px solid var(--border);
          display: flex; align-items: center; gap: 16px; background: var(--bg2); }
.search-box { flex: 1; max-width: 480px; padding: 8px 14px; border-radius: 6px;
              border: 1px solid var(--border); background: var(--bg); color: var(--text);
              font-size: 14px; outline: none; }
.search-box:focus { border-color: var(--accent); }
.search-results { position: absolute; top: 100%; left: 0; right: 0; background: var(--bg2);
                  border: 1px solid var(--border); border-radius: 6px; max-height: 400px;
                  overflow-y: auto; display: none; z-index: 100; }
.search-result { padding: 10px 14px; cursor: pointer; border-bottom: 1px solid var(--border); }
.search-result:hover { background: var(--hover); }
.search-result-title { font-weight: 600; font-size: 14px; }
.search-result-desc { font-size: 12px; color: var(--text2); margin-top: 2px; }
.search-wrapper { position: relative; flex: 1; max-width: 480px; }

.content { padding: 32px; max-width: 900px; }
.content h1 { font-size: 28px; margin-bottom: 8px; color: var(--text); }
.content h2 { font-size: 22px; margin: 24px 0 12px; color: var(--text);
              border-bottom: 1px solid var(--border); padding-bottom: 6px; }
.content h3 { font-size: 18px; margin: 20px 0 8px; color: var(--text); }
.content p { line-height: 1.7; margin-bottom: 12px; color: var(--text2); }
.content ul, .content ol { margin: 12px 0 16px 24px; color: var(--text2); }
.content ul { list-style: none; }
.content ul li { position: relative; padding-left: 20px; margin-bottom: 8px; }
.content ul li::before { content: "•"; position: absolute; left: 0; color: var(--accent); font-weight: bold; }
.content ol { list-style: decimal; }
.content ol li { margin-bottom: 8px; padding-left: 4px; }
.content li { line-height: 1.6; margin-left: 16px; }
.content li ul, .content li ol { margin: 6px 0 6px 16px; }
.content code { background: var(--code-bg); padding: 2px 6px; border-radius: 4px;
                font-size: 13px; font-family: 'SF Mono', 'Fira Code', monospace; }
.content pre { background: var(--code-bg); padding: 16px; border-radius: 8px;
               overflow: auto; margin: 12px 0; border: 1px solid var(--border); }
.content pre code { background: none; padding: 0; font-size: 13px; line-height: 1.5; }
.content blockquote { border-left: 3px solid var(--accent); padding: 8px 16px;
                      margin: 12px 0; background: rgba(88,166,255,0.05); color: var(--text2); }
.content table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; }
.content th { text-align: left; padding: 8px; border-bottom: 2px solid var(--border);
              color: var(--text); font-weight: 600; }
.content td { padding: 8px; border-bottom: 1px solid var(--border); color: var(--text2); }

.code-block { margin: 12px 0 16px; }
.code-block.collapsed pre { max-height: 360px; }
.code-block.expanded pre { max-height: none; }
.code-block-toggle { display: inline-flex; align-items: center; gap: 6px; margin-top: 8px;
                      padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px;
                      background: var(--bg2); color: var(--text2); cursor: pointer; font-size: 12px; }
.code-block-toggle:hover { background: var(--hover); color: var(--text); }
.mermaid-wrapper { margin: 12px 0 16px; padding: 16px; border: 1px solid var(--border);
                    border-radius: 8px; background: var(--bg2); overflow: auto; }
.mermaid { min-height: 24px; }
.mermaid-error { margin: 12px 0 16px; padding: 12px 14px; border: 1px solid #5a1d1d;
                  border-radius: 8px; background: rgba(248,81,73,0.08); color: #ffb4ac;
                  font-size: 13px; }

/* Cards */
.card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px;
        padding: 20px; margin-bottom: 16px; }
.card-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.card-desc { font-size: 14px; color: var(--text2); line-height: 1.6; }

/* Concept cards */
.concept-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.concept-card { display: block; background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px;
                padding: 16px; cursor: pointer; transition: all 0.15s; color: inherit; }
.concept-card:hover { border-color: var(--accent); transform: translateY(-2px); text-decoration: none; }
.concept-name { font-size: 16px; font-weight: 600; color: var(--accent); margin-bottom: 4px; }
.concept-meta { font-size: 12px; color: var(--text3); }
.concept-files { font-size: 12px; color: var(--text2); margin-top: 6px; }
.concept-card-summary { font-size: 13px; color: var(--text2); margin-top: 8px; line-height: 1.5; }
.concept-section { margin: 24px 0 28px; padding: 20px; border: 1px solid var(--border);
                   border-radius: 10px; background: var(--card-bg); }
.concept-section h3 { margin-top: 0; }
.concept-section-meta { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 14px; }
.concept-pill { display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 999px;
                border: 1px solid var(--border); background: var(--bg2); font-size: 12px; color: var(--text2); }
.concept-list { margin: 8px 0 0 18px; }
.concept-list li { margin-bottom: 6px; }
.concept-flow { margin-top: 8px; font-size: 13px; color: var(--text2); }

/* Usage badge */
.usage-badge { display: inline-block; padding: 4px 10px; background: rgba(63,185,80,0.1);
               border: 1px solid rgba(63,185,80,0.3); border-radius: 12px;
               font-size: 12px; color: var(--accent2); }

/* Page meta */
.page-meta { font-size: 12px; color: var(--text3); margin-bottom: 24px; }

/* Responsive */
@media (max-width: 768px) {
    .sidebar { display: none; }
    .main { margin-left: 0; }
}
"""


def _render_markdown_js() -> str:
    """Return JS that renders markdown content and handles search."""
    return """
// Simple markdown renderer (headings, code blocks, bold, links, lists, tables)
function renderMd(md) {
    if (!md) return '';
    let html = md;
    // Code blocks
    html = html.replace(/```(\\w*)\\n([\\s\\S]*?)```/g, function(m, lang, code) {
        if ((lang || '').toLowerCase() === 'mermaid') {
            return '<div class="mermaid-wrapper"><div class="mermaid">' + escHtml(code.trim()) + '</div></div>';
        }
        return '<pre><code class="lang-' + lang + '">' + escHtml(code.trim()) + '</code></pre>';
    });
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold
    html = html.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
    // Italic
    html = html.replace(/\\*(.+?)\\*/g, '<em>$1</em>');
    // Headers
    html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    // Links
    html = html.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, '<a href="$2">$1</a>');
    // Blockquotes
    html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
    // Unordered lists
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\\/li>\\n?)+/g, '<ul>$&</ul>');
    // Ordered lists
    html = html.replace(/^\\d+\\. (.+)$/gm, '<li>$1</li>');
    // Tables (basic)
    html = html.replace(/^\\|(.+)\\|$/gm, function(m, row) {
        if (row.match(/^[\\s\\-|:]+$/)) return '';
        let cells = row.split('|').map(c => c.trim()).filter(Boolean);
        let tag = 'td';
        return '<tr>' + cells.map(c => '<' + tag + '>' + c + '</' + tag + '>').join('') + '</tr>';
    });
    html = html.replace(/(<tr>.*<\\/tr>\\n?)+/g, '<table>$&</table>');
    // Paragraphs
    html = html.replace(/^(?!<[hupoltb]|<blockquote|<li|<tr|<table|<div)(.+)$/gm, '<p>$1</p>');
    return html;
}
function escHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// Page navigation
var pages = globalThis.pages || {};
var conceptIndex = globalThis.conceptIndex || [];
function loadPage(pageId) {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    let navEl = document.querySelector('[data-page="' + pageId + '"]');
    if (navEl) navEl.classList.add('active');
    let content = pages[pageId] || '<p>Page not found.</p>';
    document.getElementById('pageContent').innerHTML = renderMd(content);
    afterRenderContent();
    window.scrollTo(0, 0);
}

async function afterRenderContent() {
    enhanceCodeBlocks();
    await renderMermaidDiagrams();
}

function enhanceCodeBlocks() {
    document.querySelectorAll('#pageContent pre').forEach(function(pre) {
        if (pre.dataset.enhanced === 'true') {
            return;
        }
        pre.dataset.enhanced = 'true';
        const code = pre.querySelector('code');
        const text = code ? code.textContent || '' : pre.textContent || '';
        const lineCount = text ? text.split('\\n').length : 0;
        if (lineCount <= 24 && pre.scrollHeight <= 420) {
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'code-block collapsed';
        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(pre);

        const toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'code-block-toggle';
        toggle.textContent = 'Expand code';
        toggle.addEventListener('click', function() {
            const expanded = wrapper.classList.toggle('expanded');
            wrapper.classList.toggle('collapsed', !expanded);
            toggle.textContent = expanded ? 'Collapse code' : 'Expand code';
        });
        wrapper.appendChild(toggle);
    });
}

async function renderMermaidDiagrams() {
    const nodes = Array.from(document.querySelectorAll('#pageContent .mermaid'));
    if (!nodes.length) {
        return;
    }
    if (!window.mermaid) {
        nodes.forEach(function(node) {
            const error = document.createElement('div');
            error.className = 'mermaid-error';
            error.textContent = 'Diagram renderer not available. Check your internet connection and reload the page.';
            node.parentNode.replaceWith(error);
        });
        return;
    }
    if (!window.__cortexMermaidInitialized) {
        window.mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose' });
        window.__cortexMermaidInitialized = true;
    }
    try {
        for (const node of nodes) {
            const graphDefinition = node.textContent || '';
            const id = 'mermaid-' + Math.random().toString(36).substr(2, 9);
            try {
                const { svg } = await window.mermaid.render(id, graphDefinition);
                const wrapper = node.closest('.mermaid-wrapper');
                if (wrapper) {
                    wrapper.innerHTML = svg;
                    wrapper.classList.add('mermaid-rendered');
                }
            } catch (innerErr) {
                console.error('Single mermaid render failed', innerErr);
            }
        }
    } catch (error) {
        console.error('Mermaid render failed', error);
        nodes.forEach(function(node) {
            const wrapper = node.closest('.mermaid-wrapper');
            if (!wrapper) {
                return;
            }
            const failure = document.createElement('div');
            failure.className = 'mermaid-error';
            failure.textContent = 'Unable to render this Mermaid diagram.';
            wrapper.replaceWith(failure);
        });
    }
}

// Search
function doSearch(query) {
    let results = document.getElementById('searchResults');
    if (!query || query.length < 2) { results.style.display = 'none'; return; }
    let q = query.toLowerCase();
    let matches = [];

    // Search concepts
    conceptIndex.forEach(function(c) {
        let score = 0;
        if (c.name.toLowerCase().includes(q)) score += 10;
        c.aliases.forEach(function(a) { if (a.toLowerCase().includes(q)) score += 8; });
        c.symbols.forEach(function(s) { if (s.toLowerCase().includes(q)) score += 2; });
        if (score > 0) matches.push({title: c.name.replace(/_/g,' '), desc: c.symbols.slice(0,3).join(', '),
            page: 'concepts', score: score, type: 'concept'});
    });

    // Search page titles and content
    Object.keys(pages).forEach(function(pid) {
        let content = (pages[pid] || '').toLowerCase();
        if (content.includes(q)) {
            let navEl = document.querySelector('[data-page="' + pid + '"]');
            let title = navEl ? navEl.textContent : pid;
            matches.push({title: title, desc: 'Page match', page: pid, score: 3, type: 'page'});
        }
    });

    matches.sort(function(a,b) { return b.score - a.score; });
    if (matches.length === 0) { results.style.display = 'none'; return; }

    let html = '';
    matches.slice(0, 10).forEach(function(m) {
        html += '<div class="search-result" onclick="loadPage(\\'' + m.page + '\\');'
            + 'document.getElementById(\\'searchResults\\').style.display=\\'none\\';">'
            + '<div class="search-result-title">' + m.title + '</div>'
            + '<div class="search-result-desc">' + m.desc + '</div></div>';
    });
    results.innerHTML = html;
    results.style.display = 'block';
}

document.addEventListener('click', function(e) {
    if (!e.target.closest('.search-wrapper')) {
        document.getElementById('searchResults').style.display = 'none';
    }
});
"""


def _build_nav_items(pack: KnowledgePack, generated_pages: list[dict]) -> str:
    """Build sidebar navigation HTML."""
    top_pages = [
        ("overview", "📖 Overview"),
        ("architecture", "🏗️ Architecture"),
        ("concepts", "💡 Concepts"),
        ("flows", "🔀 Code Flows"),
        ("api", "📡 API Reference"),
        ("getting_started", "🚀 Getting Started"),
    ]

    nav_html = '<div class="nav-section"><div class="nav-title">Documentation</div>'
    for page_id, label in top_pages:
        active = ' active' if page_id == "overview" else ''
        nav_html += f'<a class="nav-item{active}" data-page="{page_id}" onclick="loadPage(\'{page_id}\')">{label}</a>'
    nav_html += '</div>'

    # Module pages
    module_pages = [p for p in generated_pages if p["page_id"].startswith("module_")]
    if module_pages:
        nav_html += '<div class="nav-section"><div class="nav-title">Modules</div>'
        for mp in module_pages[:20]:
            mod_name = mp["page_id"].replace("module_", "")
            short = mod_name.split("/")[-1].split("\\")[-1] if "/" in mod_name or "\\" in mod_name else mod_name
            page_id_js = mp["page_id"].replace("\\", "\\\\")
            nav_html += f'<a class="nav-item" data-page="{mp["page_id"]}" onclick="loadPage(\'{page_id_js}\')">{short}</a>'
        nav_html += '</div>'

    # Meta
    nav_html += '<div class="nav-section"><div class="nav-title">Meta</div>'
    nav_html += '<a class="nav-item" data-page="generation_report" onclick="loadPage(\'generation_report\')">📊 Generation Report</a>'
    nav_html += '</div>'

    return nav_html


def _concept_slug(name: str) -> str:
    return name.replace("_", "-").replace(" ", "-").lower()


def _build_concept_directory(concepts: list[ConceptEntry]) -> str:
    if not concepts:
        return "<p>No concepts were detected in this codebase.</p>"

    cards = []
    for c in concepts:
        name_display = html.escape(c.name.replace("_", " ").title())
        slug = _concept_slug(c.name)
        aliases = ", ".join(html.escape(a) for a in c.aliases[:3]) or "No aliases"
        syms = ", ".join(f"<code>{html.escape(s)}</code>" for s in c.related_symbols[:4]) or "No mapped symbols"
        cards.append(
            f'<a class="concept-card" href="#concept-{slug}" onclick="setTimeout(function(){{ var el = document.getElementById(\'concept-{slug}\'); if (el) el.scrollIntoView({{behavior: \'smooth\', block: \'start\'}}); }}, 0)">'
            f'<div class="concept-name">{name_display}</div>'
            f'<div class="concept-meta">{len(c.related_symbols)} symbols · {len(c.related_files)} files</div>'
            f'<div class="concept-files">{syms}</div>'
            f'<div class="concept-card-summary">Aliases: {aliases}</div>'
            f'</a>'
        )
    return '<div class="concept-grid">' + "\n".join(cards) + '</div>'


def _build_concept_sections(concepts: list[ConceptEntry]) -> str:
    if not concepts:
        return ""

    sections = []
    for c in concepts:
        slug = _concept_slug(c.name)
        name_display = html.escape(c.name.replace("_", " ").title())
        aliases = "".join(f'<span class="concept-pill">{html.escape(alias)}</span>' for alias in c.aliases[:6])
        counts = (
            f'<span class="concept-pill">{len(c.related_symbols)} symbols</span>'
            f'<span class="concept-pill">{len(c.related_files)} files</span>'
            f'<span class="concept-pill">{len(c.related_flows)} flows</span>'
        )
        symbol_items = "".join(f'<li><code>{html.escape(sym)}</code></li>' for sym in c.related_symbols[:8])
        file_items = "".join(f'<li><code>{html.escape(fp)}</code></li>' for fp in c.related_files[:6])
        flow_items = "".join(
            f'<div class="concept-flow">{html.escape(" → ".join(flow[:6]))}</div>'
            for flow in c.related_flows[:3]
        ) or '<div class="concept-flow">No direct flow mapping available.</div>'
        sections.append(
            f'<div class="concept-section" id="concept-{slug}">'
            f'<h3>{name_display}</h3>'
            f'<div class="concept-section-meta">{counts}{aliases}</div>'
            f'<p>Related code areas for this concept. Use these as entry points when exploring how this part of the system works.</p>'
            f'<h4>Key symbols</h4>'
            f'<ul class="concept-list">{symbol_items or "<li>No symbols mapped.</li>"}</ul>'
            f'<h4>Key files</h4>'
            f'<ul class="concept-list">{file_items or "<li>No files mapped.</li>"}</ul>'
            f'<h4>Observed flows</h4>'
            f'{flow_items}'
            f'</div>'
        )
    return "\n".join(sections)


def _js_safe_json(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=True, indent=None, separators=(",", ":"))
    )


def generate_wiki_site(
    pack: KnowledgePack,
    output_dir: Path,
    generated_page_files: dict[str, str] | None = None,
) -> Path:
    """Generate the multi-page CodeWiki HTML site.

    Args:
        pack: The KnowledgePack with project data and concepts.
        output_dir: Directory where markdown pages were written.
        generated_page_files: Map of page_id -> output_file for generated pages.

    Returns:
        Path to the generated index.html.
    """
    output_dir = Path(output_dir)

    # Load generated markdown pages
    page_contents: dict[str, str] = {}
    page_list: list[dict] = []

    if generated_page_files:
        for page_id, output_file in generated_page_files.items():
            md_path = output_dir / output_file
            if md_path.exists():
                content = md_path.read_text(encoding="utf-8")
                page_contents[page_id] = content
                page_list.append({"page_id": page_id, "output_file": output_file})

    concept_directory_html = _build_concept_directory(pack.concepts)
    concept_sections_html = _build_concept_sections(pack.concepts)

    # If concepts page exists, prepend the concept directory and append concept sections
    if "concepts" in page_contents:
        page_contents["concepts"] = (
            "# Concepts Guide\n\n"
            "Browse the key concepts in this project. Use the directory to jump to a concept section and inspect the mapped symbols, files, and flows.\n\n"
            + concept_directory_html
            + "\n\n"
            + page_contents["concepts"]
            + "\n\n## Concept Directory Details\n\n"
            + concept_sections_html
            + "\n"
        )

    # Load generation report if available
    report_path = output_dir / "GENERATION_REPORT.md"
    if report_path.exists():
        page_contents["generation_report"] = report_path.read_text(encoding="utf-8")

    # Build usage summary
    usage_summary = ""
    if pack.usage_records:
        agg = aggregate_usage(pack.usage_records)
        usage_summary = (
            f'<span class="usage-badge">'
            f'{agg["total_tokens"]:,} tokens · {agg["generated_pages"]} pages'
            f'</span>'
        )

    # Build concept index for search
    concept_index_json = _js_safe_json([
        {
            "name": c.name,
            "aliases": c.aliases,
            "symbols": c.related_symbols[:10],
            "files": c.related_files[:5],
        }
        for c in pack.concepts
    ])

    # Build page data JS with proper escaping
    # Use json.dumps with ensure_ascii=False and then escape any remaining issues
    pages_json = _js_safe_json(page_contents)
    data_js = "globalThis.pages = " + pages_json + ";\n"
    data_js += "globalThis.conceptIndex = " + concept_index_json + ";\n"
    data_js += "console.log('Page keys:', Object.keys(globalThis.pages || {}));\n"

    nav_html = _build_nav_items(pack, page_list)

    data_js_path = output_dir / "wiki-data.js"
    data_js_path.write_text(data_js, encoding="utf-8")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{pack.project_name} — CortexCode Wiki</title>
    <style>{_css()}</style>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
    <script src="wiki-data.js"></script>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h1>📘 {pack.project_name}</h1>
            <p>{pack.file_count} files · {pack.symbol_count} symbols · {', '.join(pack.languages[:4])}</p>
        </div>
        {nav_html}
    </div>

    <div class="main">
        <div class="topbar">
            <div class="search-wrapper">
                <input type="text" class="search-box" placeholder="Ask anything... e.g. &quot;how does authentication work?&quot;"
                       oninput="doSearch(this.value)" autocomplete="off">
                <div class="search-results" id="searchResults"></div>
            </div>
            {usage_summary}
        </div>

        <div class="content" id="pageContent">
            <h1>Loading...</h1>
        </div>
    </div>

    <script>
    {_render_markdown_js()}

    // Load initial page
    loadPage('overview');
    </script>
</body>
</html>"""

    index_path = output_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    return index_path
