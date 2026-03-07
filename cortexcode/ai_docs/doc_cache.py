import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional


CACHE_DIR = Path.home() / ".cortexcode" / "ai_cache"


def get_cache_path(prompt_hash: str) -> Path:
    """Get cache file path for a prompt."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{prompt_hash}.json"


def get_prompt_hash(messages: List[Dict[str, str]], doc_type: str) -> str:
    """Generate hash for prompt cache key."""
    content = json.dumps({"messages": messages, "type": doc_type})
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def load_cached_response(prompt_hash: str) -> Optional[str]:
    """Load cached AI response if available."""
    cache_path = get_cache_path(prompt_hash)
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            return data.get("response")
        except Exception:
            pass
    return None


def save_cached_response(prompt_hash: str, response: str) -> None:
    """Save AI response to cache."""
    cache_path = get_cache_path(prompt_hash)
    cache_path.write_text(
        json.dumps({"response": response, "cached": True}),
        encoding="utf-8",
    )
