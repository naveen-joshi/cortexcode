"""Main documentation generator - orchestrates all doc generation."""

import json
from pathlib import Path
from typing import Any

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
from cortexcode.reports.html.dashboard import generate_html_docs as generate_html_dashboard
from cortexcode.reports.html.view_model import build_dashboard_view_model
from cortexcode.reports.markdown import (
    generate_api_docs as generate_api_markdown,
    generate_flow_docs as generate_flow_markdown,
    generate_insights_docs as generate_insights_markdown,
    generate_readme as generate_readme_markdown,
    generate_structure_docs as generate_structure_markdown,
    generate_tech_docs as generate_tech_markdown,
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
    generate_tech_docs(index, output_dir / "TECH.md")
    generate_insights_docs(index, output_dir / "INSIGHTS.md")
    generate_html_docs(index, output_dir / "index.html", d3_src=d3_src)


def generate_readme(index: dict, output_path: Path) -> None:
    """Generate project README."""
    generate_readme_markdown(index, output_path)


def generate_api_docs(index: dict[str, Any], output_path: Path) -> None:
    """Generate API documentation with enhanced metadata."""
    generate_api_markdown(index, output_path)


def generate_structure_docs(index: dict, output_path: Path) -> None:
    """Generate project structure documentation."""
    generate_structure_markdown(index, output_path)


def generate_flow_docs(index: dict, output_path: Path) -> None:
    """Generate call flow documentation with cross-references."""
    generate_flow_markdown(index, output_path)


def generate_tech_docs(index: dict[str, Any], output_path: Path) -> None:
    generate_tech_markdown(index, output_path)


def generate_insights_docs(index: dict[str, Any], output_path: Path) -> None:
    generate_insights_markdown(index, output_path)


def generate_html_docs(index: dict, output_path: Path, d3_src: str = D3_CDN_URL) -> None:
    """Generate interactive HTML documentation."""
    generate_html_dashboard(index, output_path, d3_src=d3_src)
