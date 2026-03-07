"""AI Configuration - Manage API keys and settings."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


CONFIG_DIR = Path.home() / ".cortexcode"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class AIConfig:
    """AI documentation configuration."""
    provider: str = "openai"
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _ensure_config_dir() -> None:
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    _ensure_config_dir()
    
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    
    return {}


def _save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    _ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_api_key(provider: str) -> Optional[str]:
    """Get API key for a provider."""
    config = _load_config()
    
    key_name = f"{provider}_api_key"
    if key_name in config:
        return config[key_name]
    
    env_mapping = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
    }
    
    return os.environ.get(env_mapping.get(provider, ""))


def set_api_key(provider: str, api_key: str) -> None:
    """Set API key for a provider."""
    config = _load_config()
    key_name = f"{provider}_api_key"
    config[key_name] = api_key
    _save_config(config)


def get_config() -> AIConfig:
    """Get AI configuration."""
    config = _load_config()
    
    return AIConfig(
        provider=config.get("ai_provider", "openai"),
        model=config.get("ai_model", "gpt-4o"),
        temperature=config.get("ai_temperature", 0.7),
        max_tokens=config.get("ai_max_tokens", 4096),
    )


def set_config(config: AIConfig) -> None:
    """Save AI configuration."""
    full_config = _load_config()
    full_config.update({
        "ai_provider": config.provider,
        "ai_model": config.model,
        "ai_temperature": config.temperature,
        "ai_max_tokens": config.max_tokens,
    })
    _save_config(full_config)


def is_configured(provider: Optional[str] = None) -> bool:
    """Check if AI is configured."""
    if provider:
        return bool(get_api_key(provider))
    
    for p in ["openai", "anthropic", "google"]:
        if get_api_key(p):
            return True
    
    return False


def print_config_status() -> None:
    """Print configuration status."""
    print("AI Configuration Status:")
    print("-" * 40)
    
    for provider in ["openai", "anthropic", "google"]:
        key = get_api_key(provider)
        if key:
            masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
            print(f"  {provider}: {masked}")
        else:
            print(f"  {provider}: Not configured")
    
    config = get_config()
    print(f"\nDefault provider: {config.provider}")
    print(f"Default model: {config.model}")
