"""Nx monorepo workspace parsing and project graph extraction.

Handles modern Nx workspaces (v15+) where project configuration lives in
individual project.json files rather than a centralized workspace.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _safe_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _find_project_jsons(root: Path) -> list[Path]:
    """Find all project.json files under apps/ and libs/ directories."""
    project_jsons: list[Path] = []
    for candidate_dir in ("apps", "libs", "packages"):
        candidate = root / candidate_dir
        if candidate.is_dir():
            for sub in candidate.rglob("project.json"):
                project_jsons.append(sub)
    return sorted(project_jsons)


def parse_nx_workspace(root: Path) -> dict[str, Any] | None:
    """Parse an Nx workspace and return project graph + path mappings.

    Returns None if the directory does not look like an Nx workspace.
    """
    root = Path(root).resolve()
    nx_json = root / "nx.json"
    if not nx_json.exists():
        return None

    nx_config = _safe_json(nx_json) or {}

    # Collect projects from project.json files
    projects: dict[str, dict[str, Any]] = {}
    for project_json_path in _find_project_jsons(root):
        data = _safe_json(project_json_path)
        if not data:
            continue
        name = data.get("name", project_json_path.parent.name)
        projects[name] = {
            "name": name,
            "projectType": data.get("projectType", "library"),
            "sourceRoot": data.get("sourceRoot", str(project_json_path.parent.relative_to(root))),
            "tags": data.get("tags", []),
            "implicitDependencies": data.get("implicitDependencies", []),
            "root": str(project_json_path.parent.relative_to(root)).replace("\\", "/"),
            "targets": data.get("targets", {}),
            "project_json": str(project_json_path.relative_to(root)).replace("\\", "/"),
        }

    if not projects:
        return None

    # Parse tsconfig.base.json for path mappings
    tsconfig_paths = _parse_tsconfig_paths(root)

    return {
        "nx_version": nx_config.get("nxVersion", nx_config.get("installationVersion")),
        "projects": projects,
        "tsconfig_paths": tsconfig_paths,
        "namedInputs": nx_config.get("namedInputs", {}),
        "targetDefaults": nx_config.get("targetDefaults", {}),
    }


def _parse_tsconfig_paths(root: Path) -> dict[str, str]:
    """Parse tsconfig.base.json (or tsconfig.json) compilerOptions.paths.

    Returns a mapping of alias -> relative directory path.
    """
    for tsconfig_name in ("tsconfig.base.json", "tsconfig.json"):
        tsconfig = root / tsconfig_name
        if not tsconfig.exists():
            continue
        data = _safe_json(tsconfig)
        if not data:
            continue
        paths = data.get("compilerOptions", {}).get("paths", {})
        result: dict[str, str] = {}
        for alias, targets in paths.items():
            if not targets:
                continue
            # Take the first mapping; remove trailing /index.ts if present
            target = targets[0]
            target = target.rstrip("/").replace("\\", "/")
            if target.endswith("/index.ts") or target.endswith("/index.tsx") or target.endswith("/index.js"):
                target = str(Path(target).parent).replace("\\", "/")
            result[alias] = target
        return result
    return {}


def nx_framework_from_executor(targets: dict[str, Any]) -> str | None:
    """Infer framework from Nx target executors / generators."""
    for target_name, target in targets.items():
        executor = target.get("executor", "")
        if not executor:
            continue

        if "@nx/angular" in executor or "@angular-devkit" in executor:
            return "angular"
        if "@nx/react" in executor or "@nx/webpack" in executor:
            return "react"
        if "@nx/next" in executor:
            return "nextjs"
        if "@nx/vue" in executor or "@nx/vite" in executor and "vue" in executor.lower():
            return "vue"
        if "@nx/nuxt" in executor:
            return "nuxt"
        if "@nx/expo" in executor:
            return "expo"
        if "@nx/react-native" in executor:
            return "react-native"
        if "@nx/nest" in executor or "@nestjs" in executor:
            return "nestjs"
        if "@nx/node" in executor or "@nx/express" in executor:
            return "nodejs"
        if "@nx/plugin" in executor:
            return "nx-plugin"

    return None


def build_nx_project_graph(workspace: dict[str, Any]) -> dict[str, list[str]]:
    """Build adjacency list of project -> dependent project names."""
    graph: dict[str, list[str]] = {}
    projects = workspace.get("projects", {})
    tsconfig_paths = workspace.get("tsconfig_paths", {})

    # Build reverse lookup: alias -> project name
    alias_to_project: dict[str, str] = {}
    for name, proj in projects.items():
        for alias, target in tsconfig_paths.items():
            if target.startswith(proj["root"] + "/") or target == proj["root"]:
                alias_to_project[alias] = name

    # Implicit dependencies from project.json
    for name, proj in projects.items():
        deps: list[str] = []
        for dep in proj.get("implicitDependencies", []):
            if dep in projects:
                deps.append(dep)
        graph[name] = deps

    return graph
