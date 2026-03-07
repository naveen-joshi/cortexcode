import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_MAX_FILE_SIZE = 1024 * 1024

MONOREPO_MARKERS = {
    "nx": "nx.json",
    "lerna": "lerna.json",
    "yarn": "package.json",
    "pnpm": "pnpm-workspace.yaml",
    "rush": "rush.json",
    "bolt": "bolt.json",
}


@dataclass
class IndexStats:
    """Statistics about the index."""
    total_files: int = 0
    total_symbols: int = 0
    languages: Dict[str, int] = field(default_factory=dict)
    file_types: Dict[str, int] = field(default_factory=dict)
    total_size: int = 0
    index_size: int = 0
    last_indexed: str = ""


def detect_monorepo(root_path: Path) -> Optional[Dict[str, Any]]:
    """Auto-detect monorepo structure and return config."""
    root_path = Path(root_path)

    nx_json = root_path / "nx.json"
    if nx_json.exists():
        try:
            data = json.loads(nx_json.read_text(encoding="utf-8"))
            projects = data.get("projects", [])
            if projects:
                return {
                    "type": "nx",
                    "include_patterns": [f"{project}/*" for project in projects[:20]],
                }
        except Exception:
            pass

    lerna_json = root_path / "lerna.json"
    if lerna_json.exists():
        try:
            data = json.loads(lerna_json.read_text(encoding="utf-8"))
            packages = data.get("packages", ["packages/*"])
            return {
                "type": "lerna",
                "include_patterns": packages[:20],
            }
        except Exception:
            pass

    package_json = root_path / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))

            if "workspaces" in data:
                workspaces = data.get("workspaces", {})
                if isinstance(workspaces, list):
                    packages = workspaces
                else:
                    packages = workspaces.get("packages", [])
                if packages:
                    return {
                        "type": "yarn",
                        "include_patterns": packages[:20],
                    }

            pnpm_workspace = root_path / "pnpm-workspace.yaml"
            if pnpm_workspace.exists():
                return {
                    "type": "pnpm",
                    "include_patterns": ["packages/*"],
                }
        except Exception:
            pass

    rush_json = root_path / "rush.json"
    if rush_json.exists():
        return {
            "type": "rush",
            "include_patterns": ["projects/*"],
        }

    return None


def get_file_size_limit(root_path: Path) -> int:
    """Get file size limit from config or return default."""
    config_file = root_path / ".cortexcode.yaml"
    if config_file.exists():
        try:
            import yaml
            data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
            if data and "indexer" in data:
                return data["indexer"].get("max_file_size", DEFAULT_MAX_FILE_SIZE)
        except Exception:
            pass
    return DEFAULT_MAX_FILE_SIZE


def should_skip_large_file(file_path: Path, max_size: int) -> bool:
    """Check if file should be skipped due to size."""
    try:
        return file_path.stat().st_size > max_size
    except OSError:
        return True


def create_default_config(root_path: Path) -> None:
    """Create a default config file with all options."""
    config_content = """# CortexCode Configuration
# https://github.com/naveen-joshi/cortexcode

indexer:
  # Include test files in indexing (default: false)
  include_tests: false
  
  # Maximum file size to index (bytes, default: 1048576 = 1MB)
  max_file_size: 1048576
  
  # Patterns to exclude from indexing
  exclude_patterns:
    - "*.generated.*"
    - "*.mock.*"
    - "dist/"
    - "build/"
    - "coverage/"
  
  # Only include paths matching these patterns (for monorepos)
  # Use this OR exclude_patterns, not both
  # include_patterns:
  #   - "apps/*"
  #   - "packages/*"
  
  # Monorepo root directory (auto-detected if not specified)
  # monorepo_root: "."
  
  # Auto-detect monorepo and apply filters (default: true)
  auto_detect_monorepo: true

ai:
  # LLM provider: openai, anthropic, google, ollama
  provider: "openai"
  
  # Model to use
  model: "gpt-4o"
  
  # Generation parameters
  temperature: 0.7
  max_tokens: 4096
  
  # Cache AI responses (default: true)
  cache_responses: true
  
  # Token budget for AI docs generation (0 = unlimited)
  token_budget: 0

# General options
watch: false
verbose: false
"""
    config_file = root_path / ".cortexcode.yaml"
    if not config_file.exists():
        config_file.write_text(config_content, encoding="utf-8")
        print(f"Created: {config_file}")
    else:
        print(f"Config already exists: {config_file}")
