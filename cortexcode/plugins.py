"""Plugin system for framework-specific extractors.

Plugins can register custom symbol extractors, framework detectors,
and post-processors that run during indexing.

Usage:
    # Create a plugin
    class MyPlugin(CortexPlugin):
        name = "my-framework"
        extensions = [".myext"]
        
        def extract_symbols(self, source, rel_path):
            return [{"name": "foo", "type": "function", "line": 1}]
        
        def detect_framework(self, name, source_str):
            if "MyFramework" in source_str:
                return "my-framework"
            return None
    
    # Register it
    plugin_registry.register(MyPlugin())
"""

import importlib
import json
from pathlib import Path
from typing import Any, Protocol


class CortexPlugin(Protocol):
    """Protocol for CortexCode plugins."""
    
    name: str
    extensions: list[str]
    
    def extract_symbols(self, source: str, rel_path: str) -> list[dict[str, Any]]:
        """Extract symbols from source code. Return list of symbol dicts."""
        ...
    
    def detect_framework(self, name: str, source_str: str) -> str | None:
        """Detect framework from symbol name and source. Return framework string or None."""
        ...
    
    def extract_imports(self, source: str) -> list[dict[str, Any]]:
        """Extract imports from source code. Return list of import dicts."""
        ...
    
    def post_process(self, index: dict[str, Any]) -> dict[str, Any]:
        """Post-process the full index after all files are indexed."""
        ...


class BasePlugin:
    """Base class for plugins with default no-op implementations."""
    
    name: str = "base"
    extensions: list[str] = []
    
    def extract_symbols(self, source: str, rel_path: str) -> list[dict[str, Any]]:
        return []
    
    def detect_framework(self, name: str, source_str: str) -> str | None:
        return None
    
    def extract_imports(self, source: str) -> list[dict[str, Any]]:
        return []
    
    def post_process(self, index: dict[str, Any]) -> dict[str, Any]:
        return index


class PluginRegistry:
    """Central registry for all CortexCode plugins."""
    
    def __init__(self):
        self._plugins: dict[str, BasePlugin] = {}
        self._ext_map: dict[str, str] = {}  # extension -> plugin name
    
    def register(self, plugin: BasePlugin) -> None:
        """Register a plugin."""
        self._plugins[plugin.name] = plugin
        for ext in plugin.extensions:
            self._ext_map[ext] = plugin.name
    
    def unregister(self, name: str) -> bool:
        """Unregister a plugin by name."""
        if name in self._plugins:
            plugin = self._plugins.pop(name)
            for ext in plugin.extensions:
                if self._ext_map.get(ext) == name:
                    del self._ext_map[ext]
            return True
        return False
    
    def get_plugin(self, name: str) -> BasePlugin | None:
        """Get a plugin by name."""
        return self._plugins.get(name)
    
    def get_plugin_for_ext(self, ext: str) -> BasePlugin | None:
        """Get the plugin registered for a file extension."""
        name = self._ext_map.get(ext)
        return self._plugins.get(name) if name else None
    
    def list_plugins(self) -> list[dict[str, Any]]:
        """List all registered plugins."""
        return [
            {
                "name": p.name,
                "extensions": p.extensions,
            }
            for p in self._plugins.values()
        ]
    
    @property
    def registered_extensions(self) -> set[str]:
        """All file extensions handled by plugins."""
        return set(self._ext_map.keys())
    
    def extract_symbols(self, source: str, ext: str, rel_path: str) -> list[dict[str, Any]] | None:
        """Try to extract symbols using a registered plugin. Returns None if no plugin handles this ext."""
        plugin = self.get_plugin_for_ext(ext)
        if plugin:
            return plugin.extract_symbols(source, rel_path)
        return None
    
    def detect_framework(self, name: str, source_str: str) -> str | None:
        """Run all plugins' framework detection. First match wins."""
        for plugin in self._plugins.values():
            result = plugin.detect_framework(name, source_str)
            if result:
                return result
        return None
    
    def extract_imports(self, source: str, ext: str) -> list[dict[str, Any]] | None:
        """Try to extract imports using a registered plugin."""
        plugin = self.get_plugin_for_ext(ext)
        if plugin:
            return plugin.extract_imports(source)
        return None
    
    def run_post_processors(self, index: dict[str, Any]) -> dict[str, Any]:
        """Run all plugins' post-processors on the index."""
        for plugin in self._plugins.values():
            index = plugin.post_process(index)
        return index
    
    def load_from_config(self, config_path: Path) -> int:
        """Load plugins from a cortexcode config file.
        
        Config format (.cortexcode/plugins.json):
        {
            "plugins": [
                {"module": "my_package.cortex_plugin", "class": "MyPlugin"},
                {"module": "another_plugin", "class": "AnotherPlugin"}
            ]
        }
        
        Returns number of plugins loaded.
        """
        if not config_path.exists():
            return 0
        
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return 0
        
        count = 0
        for entry in data.get("plugins", []):
            module_name = entry.get("module")
            class_name = entry.get("class")
            if not module_name or not class_name:
                continue
            
            try:
                mod = importlib.import_module(module_name)
                cls = getattr(mod, class_name)
                plugin = cls()
                self.register(plugin)
                count += 1
            except (ImportError, AttributeError, TypeError) as e:
                print(f"Failed to load plugin {module_name}.{class_name}: {e}")
        
        return count


# Global plugin registry
plugin_registry = PluginRegistry()
