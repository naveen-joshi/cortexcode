"""Integration tests for Nx import resolution in indexing pipeline."""
import json
import tempfile
from pathlib import Path

from cortexcode.indexing.resolution import (
    build_file_dependencies,
    build_type_map,
    candidate_module_keys,
    resolve_import_to_files,
    build_module_lookup,
)


def test_candidate_module_keys_with_tsconfig_paths():
    tsconfig_paths = {
        "@myorg/shared-ui": "libs/shared-ui/src",
        "@myorg/data": "libs/data/src",
    }

    imp = {"module": "@myorg/shared-ui", "imported": ["Button"]}
    candidates = candidate_module_keys("apps/app/src/main.tsx", imp, tsconfig_paths)
    assert "libs/shared-ui/src" in candidates
    assert "libs/shared-ui/src/Button" in candidates

    imp = {"module": "@myorg/shared-ui/components", "imported": []}
    candidates = candidate_module_keys("apps/app/src/main.tsx", imp, tsconfig_paths)
    assert "libs/shared-ui/src/components" in candidates


def test_resolve_import_to_files_with_tsconfig():
    file_symbols = {
        "libs/shared-ui/src/index.ts": {
            "symbols": [{"name": "Button", "type": "function"}],
            "imports": [],
        },
        "libs/shared-ui/src/Button.tsx": {
            "symbols": [{"name": "Button", "type": "function"}],
            "imports": [],
        },
        "apps/app/src/main.tsx": {
            "symbols": [],
            "imports": [{"module": "@myorg/shared-ui", "imported": ["Button"]}],
        },
    }
    tsconfig_paths = {"@myorg/shared-ui": "libs/shared-ui/src"}
    deps = build_file_dependencies(file_symbols, tsconfig_paths)
    assert "apps/app/src/main.tsx" in deps
    # Should resolve to either index.ts or Button.tsx depending on lookup
    assert len(deps["apps/app/src/main.tsx"]) > 0


def test_build_type_map_with_tsconfig():
    file_symbols = {
        "libs/data/src/index.ts": {
            "symbols": [{"name": "User", "type": "class"}],
            "imports": [],
        },
        "apps/app/src/main.tsx": {
            "symbols": [],
            "imports": [{"module": "@myorg/data", "imported": ["User"]}],
        },
    }
    tsconfig_paths = {"@myorg/data": "libs/data/src"}
    type_map = build_type_map(file_symbols, tsconfig_paths)
    key = "apps/app/src/main.tsx:User"
    assert key in type_map
    assert type_map[key]["defined_in"] == "libs/data/src/index.ts"


def test_build_type_map_traces_reexports():
    file_symbols = {
        "libs/shared/ui/src/index.ts": {
            "symbols": [],
            "imports": [],
            "exports": [{"name": "Button", "type": "re-export", "source": "./lib/button"}],
        },
        "libs/shared/ui/src/lib/button.tsx": {
            "symbols": [{"name": "Button", "type": "function"}],
            "imports": [],
            "exports": [{"name": "Button", "type": "function"}],
        },
        "apps/store/src/app/main.tsx": {
            "symbols": [],
            "imports": [{"module": "@nx-example/shared/ui", "imported": ["Button"]}],
        },
    }
    tsconfig_paths = {"@nx-example/shared/ui": "libs/shared/ui/src"}
    type_map = build_type_map(file_symbols, tsconfig_paths)
    key = "apps/store/src/app/main.tsx:Button"
    assert key in type_map
    assert type_map[key]["defined_in"] == "libs/shared/ui/src/lib/button.tsx"
    assert type_map[key]["type"] == "function"


def test_build_file_dependencies_without_tsconfig():
    file_symbols = {
        "src/a.ts": {"symbols": [], "imports": [{"module": "./b", "imported": []}]},
        "src/b.ts": {"symbols": [], "imports": []},
    }
    deps = build_file_dependencies(file_symbols)
    assert deps == {"src/a.ts": ["src/b.ts"]}


if __name__ == "__main__":
    test_candidate_module_keys_with_tsconfig_paths()
    test_resolve_import_to_files_with_tsconfig()
    test_build_type_map_with_tsconfig()
    test_build_file_dependencies_without_tsconfig()
    print("All Nx resolution tests passed!")
