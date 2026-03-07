import json
from typing import Any


def build_framework_cards_html(profile_frameworks: list[dict[str, Any]], framework_counts: dict[str, int]) -> str:
    if profile_frameworks:
        framework_items = "".join(
            f'<div style="background:var(--bg);padding:12px 20px;border-radius:var(--radius-sm);text-align:center;">'
            f'<div style="font-size:24px;font-weight:700;color:var(--accent);">{framework.get("count", 0)}</div>'
            f'<div style="font-size:12px;color:var(--text3);margin-top:2px;">{framework.get("name", "unknown")}</div></div>'
            for framework in profile_frameworks[:8]
        )
        return (
            '<div class="card"><div class="card-title">Detected Frameworks</div>'
            '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px;">'
            f'{framework_items}</div></div>'
        )

    if any(framework_counts.values()):
        framework_items = "".join(
            f'<div style="background:var(--bg);padding:12px 20px;border-radius:var(--radius-sm);text-align:center;">'
            f'<div style="font-size:24px;font-weight:700;color:var(--accent);">{count}</div>'
            f'<div style="font-size:12px;color:var(--text3);margin-top:2px;">{framework}</div></div>'
            for framework, count in framework_counts.items() if count > 0
        )
        return (
            '<div class="card"><div class="card-title">Detected Frameworks</div>'
            '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px;">'
            f'{framework_items}</div></div>'
        )

    return ""


def build_layer_cards_html(profile_layers: list[dict[str, Any]]) -> str:
    if not profile_layers:
        return ""

    layer_items = "".join(
        f'<div style="background:var(--bg);padding:12px 20px;border-radius:var(--radius-sm);min-width:160px;">'
        f'<div style="font-size:16px;font-weight:700;color:var(--text1);">{layer.get("name", "unknown")}</div>'
        f'<div style="font-size:12px;color:var(--text3);margin-top:6px;">{layer.get("files", 0)} files · {layer.get("symbols", 0)} symbols</div>'
        f'</div>'
        for layer in profile_layers[:8]
    )
    return (
        '<div class="card"><div class="card-title">Architecture Layers</div>'
        '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px;">'
        f'{layer_items}</div></div>'
    )


def build_insight_cards_html(profile_entry_points: list[dict[str, Any]], profile_recommendations: dict[str, Any]) -> str:
    if not profile_entry_points and not profile_recommendations:
        return ""

    entry_point_items = "".join(
        f'<div style="margin-top:8px;color:var(--text2);font-size:13px;">• {entry_point.get("name", "unknown")} <span style="color:var(--text3);">({entry_point.get("reason", "detected")})</span></div>'
        for entry_point in profile_entry_points[:5]
    )
    recommendation_items = "".join(
        f'<span style="display:inline-block;background:var(--bg);padding:6px 10px;border-radius:999px;margin:4px 6px 0 0;font-size:12px;color:var(--accent);">{report_name}</span>'
        for report_name in profile_recommendations.get("reports", [])[:6]
    )
    empty_entry_points_html = '<div style="margin-top:8px;color:var(--text3);font-size:13px;">No entry points inferred</div>'
    return (
        '<div class="card"><div class="card-title">Suggested Exploration</div>'
        '<div class="card-subtitle">Entry points and next reports</div>'
        f'{entry_point_items or empty_entry_points_html}'
        f'<div style="margin-top:14px;">{recommendation_items}</div></div>'
    )


def build_filter_tabs_html(type_counts: dict[str, int]) -> str:
    return "".join(
        f'<div class="filter-tab" onclick="filterByType(\'{symbol_type}\', this)">{symbol_type.title()} ({count})</div>'
        for symbol_type, count in sorted(type_counts.items(), key=lambda item: -item[1])
    )


def build_top_files_rows_html(files_with_most_symbols: list[dict[str, Any]]) -> str:
    max_count = files_with_most_symbols[0]["count"] if files_with_most_symbols else 1
    return "".join(
        f'<tr><td style="color:var(--text2);font-size:12px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{item["file"]}">{item["file"]}</td>'
        f'<td style="font-weight:600;color:var(--accent);">{item["count"]}</td>'
        f'<td><div class="bar" style="width:{min(100, item["count"] * 100 // max(1, max_count))}%;"></div></td></tr>'
        for item in files_with_most_symbols[:8]
    )


def build_top_callers_rows_html(top_callers: list[tuple[str, int]]) -> str:
    max_count = top_callers[0][1] if top_callers else 1
    return "".join(
        f'<tr><td style="color:var(--accent);font-size:13px;cursor:pointer;" onclick="highlightGraphNode(\'{name}\')">{name}</td>'
        f'<td style="font-weight:600;">{count}</td>'
        f'<td><div class="bar" style="width:{min(100, count * 100 // max(1, max_count))}%;background:var(--accent2);"></div></td></tr>'
        for name, count in top_callers[:8]
    )


def build_search_data_json(all_symbols: list[dict[str, Any]]) -> str:
    return json.dumps([
        {
            "name": symbol.get("name", ""),
            "type": symbol.get("type", ""),
            "file": symbol.get("file", ""),
            "line": symbol.get("line", 0),
            "doc": (symbol.get("doc", "") or "")[:60],
            "params": symbol.get("params", [])[:3],
        }
        for symbol in all_symbols if isinstance(symbol, dict)
    ][:600])


def build_dashboard_js_code(
    *,
    call_graph: dict[str, Any],
    file_deps: dict[str, Any],
    type_counts: dict[str, int],
    language_counts: dict[str, int],
    type_colors: dict[str, str],
    lang_colors: dict[str, str],
    all_symbols: list[dict[str, Any]],
    js_template: str,
) -> str:
    return js_template.format(
        call_graph_json=json.dumps(call_graph),
        file_deps_json=json.dumps(file_deps),
        type_counts_json=json.dumps(type_counts),
        lang_counts_json=json.dumps(language_counts),
        type_colors_json=json.dumps(type_colors),
        lang_colors_json=json.dumps(lang_colors),
        search_data_json=build_search_data_json(all_symbols),
    )
