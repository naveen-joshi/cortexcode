"""LLM Client - Multi-provider LLM integration for AI documentation."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]
    cost: Optional[float] = None


class LLMClient:
    """Multi-provider LLM client with configurable API keys."""

    def __init__(
        self,
        provider: LLMProvider = LLMProvider.OPENAI,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.provider = provider
        self.api_key = api_key or self._load_api_key(provider)
        self.model = model or self._default_model(provider)
        self.base_url = base_url

    def _load_api_key(self, provider: LLMProvider) -> Optional[str]:
        """Load API key from config file or environment."""
        config_path = Path.home() / ".cortexcode" / "config.json"
        
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                key_name = f"{provider.value}_api_key"
                if key_name in config:
                    return config[key_name]
            except Exception:
                pass
        
        env_mapping: Dict[LLMProvider, List[str]] = {
            LLMProvider.OPENAI: ["OPENAI_API_KEY"],
            LLMProvider.ANTHROPIC: ["ANTHROPIC_API_KEY"],
            LLMProvider.GOOGLE: ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
            LLMProvider.OLLAMA: ["OLLAMA_BASE_URL"],
        }
        
        for env_var in env_mapping.get(provider, []):
            val = os.environ.get(env_var)
            if val:
                return val
        return None

    def _default_model(self, provider: LLMProvider) -> str:
        """Get default model for provider."""
        defaults = {
            LLMProvider.OPENAI: "gpt-4o",
            LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
            LLMProvider.GOOGLE: "gemini-3-flash-preview",
            LLMProvider.OLLAMA: "llama3",
        }
        return defaults.get(provider, "gpt-4o")

    def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send completion request to LLM."""
        if self.provider == LLMProvider.OPENAI:
            return self._openai_complete(messages, temperature, max_tokens)
        elif self.provider == LLMProvider.ANTHROPIC:
            return self._anthropic_complete(messages, temperature, max_tokens)
        elif self.provider == LLMProvider.GOOGLE:
            return self._google_complete(messages, temperature, max_tokens)
        elif self.provider == LLMProvider.OLLAMA:
            return self._ollama_complete(messages, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _openai_complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
    ) -> LLMResponse:
        """OpenAI API completion."""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage=usage,
        )

    def _anthropic_complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
    ) -> LLMResponse:
        """Anthropic API completion."""
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")

        client = anthropic.Anthropic(api_key=self.api_key)
        
        system = ""
        filtered_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system = msg.get("content", "")
            else:
                filtered_messages.append(msg)

        response = client.messages.create(
            model=self.model,
            system=system,
            messages=filtered_messages,
            temperature=temperature,
            max_tokens=max_tokens or 4096,
        )
        
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }
        
        return LLMResponse(
            content=response.content[0].text,
            model=self.model,
            usage=usage,
        )

    def _google_complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
    ) -> LLMResponse:
        """Google Gemini API completion using the google-genai SDK."""
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError("google-genai package required. Install with: pip install google-genai")

        client = genai.Client(api_key=self.api_key)

        # Build contents: combine system instruction + user messages
        system_instruction = None
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            if role == "system":
                system_instruction = text
            else:
                contents.append(types.Content(
                    role="user" if role == "user" else "model",
                    parts=[types.Part(text=text)],
                ))

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system_instruction:
            config.system_instruction = system_instruction

        response = client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        # Best-effort token reporting for Gemini
        usage: Dict[str, int] = {"total_tokens": 0}
        try:
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                um = response.usage_metadata
                prompt_tokens = getattr(um, "prompt_token_count", 0) or 0
                completion_tokens = getattr(um, "candidates_token_count", 0) or 0
                total = getattr(um, "total_token_count", 0) or (prompt_tokens + completion_tokens)
                usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total,
                }
        except Exception:
            pass

        return LLMResponse(
            content=response.text,
            model=self.model,
            usage=usage,
        )

    def _ollama_complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
    ) -> LLMResponse:
        """Ollama local model completion."""
        import requests
        
        base_url = self.base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "options": {"num_predict": max_tokens},
            },
        )
        response.raise_for_status()
        
        data = response.json()
        return LLMResponse(
            content=data["message"]["content"],
            model=self.model,
            usage={"total_tokens": 0},
        )

    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)


def get_available_providers() -> List[str]:
    """Get list of available (configured) providers."""
    providers = []
    
    config_path = Path.home() / ".cortexcode" / "config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            for provider in LLMProvider:
                key_name = f"{provider.value}_api_key"
                if config.get(key_name):
                    providers.append(provider.value)
                    continue
        except Exception:
            pass
    
    for provider in LLMProvider:
        if provider.value.upper() in os.environ:
            if provider.value not in providers:
                providers.append(provider.value)
    
    return providers
