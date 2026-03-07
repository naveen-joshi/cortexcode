"""Token usage accounting for AI report generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cortexcode.knowledge.models import UsageRecord


def aggregate_usage(records: list[UsageRecord]) -> dict[str, Any]:
    """Compute aggregate token usage from a list of records."""
    total_prompt = sum(r.prompt_tokens for r in records)
    total_completion = sum(r.completion_tokens for r in records)
    total_tokens = sum(r.total_tokens for r in records)
    cached_count = sum(1 for r in records if r.cached)
    generated_count = sum(1 for r in records if not r.cached)
    total_cost = sum(r.cost_estimate for r in records if r.cost_estimate is not None)

    providers = set(r.provider for r in records)
    models = set(r.model for r in records)

    return {
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_tokens": total_tokens,
        "cached_pages": cached_count,
        "generated_pages": generated_count,
        "total_pages": len(records),
        "total_cost_estimate": round(total_cost, 6) if total_cost else None,
        "providers": sorted(providers),
        "models": sorted(models),
    }


def format_usage_cli(records: list[UsageRecord]) -> str:
    """Format usage records as a human-readable CLI summary."""
    agg = aggregate_usage(records)
    lines = [
        "╭──────── Generation Report ────────╮",
        f"│ Pages generated    {agg['generated_pages']:>14} │",
        f"│ Pages from cache   {agg['cached_pages']:>14} │",
        f"│ Total pages        {agg['total_pages']:>14} │",
        f"│                                   │",
        f"│ Prompt tokens      {agg['total_prompt_tokens']:>14,} │",
        f"│ Completion tokens  {agg['total_completion_tokens']:>14,} │",
        f"│ Total tokens       {agg['total_tokens']:>14,} │",
    ]
    if agg["total_cost_estimate"] is not None:
        lines.append(f"│ Est. cost          ${agg['total_cost_estimate']:>13.6f} │")
    lines.append(f"│                                   │")
    lines.append(f"│ Provider(s)  {', '.join(agg['providers']):>20} │")
    lines.append(f"│ Model(s)     {', '.join(agg['models']):>20} │")
    lines.append("╰───────────────────────────────────╯")
    return "\n".join(lines)


def format_usage_table(records: list[UsageRecord]) -> str:
    """Format per-page usage as a markdown table."""
    lines = [
        "| Page | Status | Prompt | Completion | Total | Model |",
        "|------|--------|-------:|-----------:|------:|-------|",
    ]
    for r in records:
        status = "cached" if r.cached else "generated"
        lines.append(
            f"| {r.page_id} | {status} | {r.prompt_tokens:,} | "
            f"{r.completion_tokens:,} | {r.total_tokens:,} | {r.model} |"
        )
    agg = aggregate_usage(records)
    lines.append(
        f"| **Total** | | **{agg['total_prompt_tokens']:,}** | "
        f"**{agg['total_completion_tokens']:,}** | **{agg['total_tokens']:,}** | |"
    )
    return "\n".join(lines)


def save_usage_report(records: list[UsageRecord], output_path: Path) -> None:
    """Save usage report as JSON."""
    agg = aggregate_usage(records)
    report = {
        "summary": agg,
        "pages": [r.to_dict() for r in records],
    }
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
