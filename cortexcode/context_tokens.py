import json
from pathlib import Path
from typing import Any

from cortexcode.context_query import get_context


_tiktoken_encoder = None
try:
    import tiktoken
    _tiktoken_encoder = tiktoken.encoding_for_model("gpt-4")
except ImportError:
    pass


def estimate_tokens(text: str) -> int:
    """Estimate token count. Uses tiktoken if available, else ~4 chars/token heuristic."""
    if _tiktoken_encoder:
        return len(_tiktoken_encoder.encode(text))
    return max(1, len(text) // 4)


def estimate_file_tokens(file_path: Path) -> int:
    """Estimate tokens for an entire file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return estimate_tokens(content)
    except OSError:
        return 0


def calculate_token_savings(index_path: Path, query: str | None = None, num_results: int = 5) -> dict[str, Any]:
    """Calculate how many tokens CortexCode saves vs reading raw files.

    Returns:
        Dictionary with token counts for raw files vs indexed context
    """
    index = json.loads(index_path.read_text(encoding="utf-8"))
    files = index.get("files", {})
    project_root = Path(index.get("project_root", "."))

    total_raw_tokens = 0
    file_count = 0
    for rel_path in files:
        full_path = project_root / rel_path
        if full_path.exists():
            total_raw_tokens += estimate_file_tokens(full_path)
            file_count += 1

    index_text = index_path.read_text(encoding="utf-8")
    index_tokens = estimate_tokens(index_text)

    result = get_context(index_path, query, num_results)
    context_text = json.dumps(result, indent=2)
    context_tokens = estimate_tokens(context_text)

    savings_vs_raw = total_raw_tokens - context_tokens
    savings_pct = (savings_vs_raw / total_raw_tokens * 100) if total_raw_tokens > 0 else 0

    return {
        "raw_project_tokens": total_raw_tokens,
        "index_tokens": index_tokens,
        "context_tokens": context_tokens,
        "savings_tokens": savings_vs_raw,
        "savings_percent": round(savings_pct, 1),
        "file_count": file_count,
        "compression_ratio": round(total_raw_tokens / context_tokens, 1) if context_tokens > 0 else 0,
    }
