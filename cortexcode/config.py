"""CortexCode Configuration - Load and manage project config."""

import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict


DEFAULT_CONFIG_FILE = ".cortexcode.yaml"


@dataclass
class IndexerConfig:
    """Indexer configuration."""
    include_tests: bool = False
    max_file_size: int = 1024 * 1024
    exclude_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    monorepo_root: Optional[str] = None


@dataclass
class AIConfig:
    """AI documentation configuration."""
    provider: str = "openai"
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class CortexCodeConfig:
    """Main CortexCode configuration."""
    indexer: IndexerConfig = field(default_factory=IndexerConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    watch: bool = False
    verbose: bool = False


def load_config(root_path: Path) -> CortexCodeConfig:
    """Load configuration from .cortexcode.yaml file."""
    config_file = root_path / DEFAULT_CONFIG_FILE
    
    if not config_file.exists():
        return CortexCodeConfig()
    
    try:
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        if not data:
            return CortexCodeConfig()
        
        config = CortexCodeConfig()
        
        # Load indexer config
        if "indexer" in data:
            idx = data["indexer"]
            config.indexer = IndexerConfig(
                include_tests=idx.get("include_tests", False),
                max_file_size=idx.get("max_file_size", 1024 * 1024),
                exclude_patterns=idx.get("exclude_patterns", []),
                include_patterns=idx.get("include_patterns", []),
                monorepo_root=idx.get("monorepo_root"),
            )
        
        # Load AI config
        if "ai" in data:
            ai = data["ai"]
            config.ai = AIConfig(
                provider=ai.get("provider", "openai"),
                model=ai.get("model", "gpt-4o"),
                temperature=ai.get("temperature", 0.7),
                max_tokens=ai.get("max_tokens", 4096),
            )
        
        # Load general config
        config.watch = data.get("watch", False)
        config.verbose = data.get("verbose", False)
        
        return config
        
    except Exception as e:
        print(f"Warning: Failed to load config: {e}")
        return CortexCodeConfig()


def save_config(config: CortexCodeConfig, root_path: Path) -> None:
    """Save configuration to .cortexcode.yaml file."""
    config_file = root_path / DEFAULT_CONFIG_FILE
    
    data = {
        "indexer": asdict(config.indexer),
        "ai": asdict(config.ai),
        "watch": config.watch,
        "verbose": config.verbose,
    }
    
    config_file.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def get_filter_opts_from_config(root_path: Path) -> Dict[str, Any]:
    """Get filter options from config file."""
    config = load_config(root_path)
    return {
        "include_tests": config.indexer.include_tests,
        "max_file_size": config.indexer.max_file_size,
        "exclude_patterns": config.indexer.exclude_patterns,
        "include_patterns": config.indexer.include_patterns,
        "monorepo_root": config.indexer.monorepo_root,
    }


def create_example_config(root_path: Path) -> None:
    """Create an example config file."""
    example_config = """# CortexCode Configuration
# https://github.com/naveen-joshi/cortexcode

indexer:
  # Include test files in indexing (default: false)
  include_tests: false
  
  # Maximum file size to index (bytes, default: 1048576 = 1MB)
  max_file_size: 1048576
  
  # Patterns to exclude from indexing
  exclude_patterns:
    - "*.generated.ts"
    - "*.mock.ts"
    - "dist/"
    - "build/"
  
  # Only include paths matching these patterns (for monorepos)
  include_patterns:
    - "apps/*"
    - "packages/*"
  
  # Monorepo root directory
  # monorepo_root: "."

ai:
  # LLM provider: openai, anthropic, google, ollama
  provider: "openai"
  
  # Model to use
  model: "gpt-4o"
  
  # Generation parameters
  temperature: 0.7
  max_tokens: 4096

# General options
watch: false
verbose: false
"""
    config_file = root_path / DEFAULT_CONFIG_FILE
    if not config_file.exists():
        config_file.write_text(example_config, encoding="utf-8")
        print(f"Created example config: {config_file}")
    else:
        print(f"Config already exists: {config_file}")
