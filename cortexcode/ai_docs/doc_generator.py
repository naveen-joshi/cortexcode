"""AI Documentation Generator - Main orchestration for AI-powered docs."""

from pathlib import Path
from typing import Dict, List, Optional

from cortexcode.ai_docs.llm_client import LLMClient, LLMProvider
from cortexcode.ai_docs.config import get_config
from cortexcode.ai_docs.doc_cache import get_prompt_hash, load_cached_response, save_cached_response
from cortexcode.ai_docs.doc_lookup import find_module_data, find_symbol_data, load_index_data
from cortexcode.ai_docs.doc_models import DocOutput
from cortexcode.ai_docs import prompts


class AIDocGenerator:
    """AI-powered documentation generator using LLM."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        cache_enabled: bool = True,
        token_budget: int = 0,
    ):
        config = get_config()
        
        self.provider_name = provider or config.provider
        self.llm = LLMClient(
            provider=LLMProvider(self.provider_name),
            api_key=api_key,
            model=model or config.model,
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.cache_enabled = cache_enabled
        self.token_budget = token_budget
        self.tokens_used = 0

    def generate_project_docs(
        self,
        index_path: Path,
        output_dir: Path,
        docs: Optional[List[str]] = None,
    ) -> DocOutput:
        """Generate AI-powered documentation for a project."""
        
        index_path = Path(index_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        index_data = load_index_data(index_path)
        
        docs = docs or ["overview", "api", "architecture", "flows"]
        output = DocOutput()
        
        if "overview" in docs:
            print("Generating project overview...")
            messages = prompts.generate_project_overview_prompt(index_data)
            output.overview = self._generate(messages, "overview")
            if output.overview:
                (output_dir / "AI_OVERVIEW.md").write_text(output.overview)
                print("  -> AI_OVERVIEW.md")
        
        if "api" in docs:
            print("Generating API documentation...")
            messages = prompts.generate_api_docs_prompt(index_data)
            output.api_docs = self._generate(messages, "api")
            if output.api_docs:
                (output_dir / "AI_API.md").write_text(output.api_docs)
                print("  -> AI_API.md")
        
        if "architecture" in docs:
            print("Generating architecture documentation...")
            messages = prompts.generate_architecture_prompt(index_data)
            output.architecture = self._generate(messages, "architecture")
            if output.architecture:
                (output_dir / "AI_ARCHITECTURE.md").write_text(output.architecture)
                print("  -> AI_ARCHITECTURE.md")
        
        if "flows" in docs:
            print("Generating code flow documentation...")
            messages = prompts.generate_flow_docs_prompt(index_data)
            output.flows = self._generate(messages, "flows")
            if output.flows:
                (output_dir / "AI_FLOWS.md").write_text(output.flows)
                print("  -> AI_FLOWS.md")
        
        return output

    def generate_module_docs(
        self,
        index_path: Path,
        module_name: str,
        output_path: Optional[Path] = None,
    ) -> str:
        """Generate documentation for a specific module."""
        
        index_data = load_index_data(index_path)
        module_data = find_module_data(index_data, module_name)
        
        if not module_data:
            return f"Module '{module_name}' not found in index."
        
        messages = prompts.generate_module_docs_prompt(module_name, module_data)
        result = self._generate(messages, f"module_{module_name}")
        
        if output_path and result:
            Path(output_path).write_text(result)
        
        return result

    def explain_symbol(
        self,
        index_path: Path,
        symbol_name: str,
    ) -> str:
        """Explain a specific symbol using AI."""
        
        index_data = load_index_data(index_path)
        symbol_data = find_symbol_data(index_data, symbol_name)
        
        if not symbol_data:
            return f"Symbol '{symbol_name}' not found in index."
        
        messages = prompts.explain_symbol_prompt(symbol_name, symbol_data, index_data)
        return self._generate(messages, f"explain_{symbol_name}")

    def _generate(self, messages: List[Dict[str, str]], doc_type: str) -> Optional[str]:
        """Generate content using LLM with caching and token budget."""
        
        if not self.llm.is_configured():
            print(f"  Error: No API key configured for {self.provider_name}")
            print(f"  Run: cortexcode config set {self.provider_name}_api_key <your-key>")
            return None
        
        # Check token budget
        if self.token_budget > 0 and self.tokens_used >= self.token_budget:
            print(f"  Warning: Token budget ({self.token_budget}) exceeded. Skipping {doc_type}")
            return None
        
        # Check cache first
        prompt_hash = get_prompt_hash(messages, doc_type)
        if self.cache_enabled:
            cached = load_cached_response(prompt_hash)
            if cached:
                print(f"  -> Using cached response for {doc_type}")
                return cached
        
        try:
            response = self.llm.complete(
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            # Track tokens used
            if response.usage:
                self.tokens_used += response.usage.get("total_tokens", 0)
            
            if self.cache_enabled:
                save_cached_response(prompt_hash, response.content)
            
            return response.content
        except Exception as e:
            print(f"  Error generating {doc_type}: {e}")
            return None


def generate_project_docs(
    index_path: Path,
    output_dir: Path,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    docs: Optional[List[str]] = None,
) -> DocOutput:
    """Convenience function to generate project documentation."""
    
    generator = AIDocGenerator(provider=provider, model=model)
    return generator.generate_project_docs(index_path, output_dir, docs)


def explain_symbol(
    index_path: Path,
    symbol_name: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """Convenience function to explain a symbol."""
    
    generator = AIDocGenerator(provider=provider, model=model)
    return generator.explain_symbol(index_path, symbol_name)
