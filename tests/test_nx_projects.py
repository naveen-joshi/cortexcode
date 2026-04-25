"""Tests for Nx monorepo workspace parsing."""
import json
import tempfile
from pathlib import Path

from cortexcode.indexing.nx_projects import (
    build_nx_project_graph,
    nx_framework_from_executor,
    parse_nx_workspace,
    _parse_tsconfig_paths,
)


def test_parse_nx_workspace_no_nx_json():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "project.json").write_text('{"name": "foo"}')
        assert parse_nx_workspace(root) is None


def test_parse_nx_workspace_simple():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "nx.json").write_text(json.dumps({"nxVersion": "16.0.0"}))

        apps_dir = root / "apps" / "my-app"
        apps_dir.mkdir(parents=True)
        (apps_dir / "project.json").write_text(json.dumps({
            "name": "my-app",
            "projectType": "application",
            "sourceRoot": "apps/my-app/src",
            "tags": ["react"],
            "targets": {"build": {"executor": "@nx/react:build"}},
        }))

        libs_dir = root / "libs" / "shared-ui"
        libs_dir.mkdir(parents=True)
        (libs_dir / "project.json").write_text(json.dumps({
            "name": "shared-ui",
            "projectType": "library",
            "sourceRoot": "libs/shared-ui/src",
            "tags": ["ui"],
            "implicitDependencies": ["my-app"],
        }))

        tsconfig = root / "tsconfig.base.json"
        tsconfig.write_text(json.dumps({
            "compilerOptions": {
                "paths": {
                    "@myorg/shared-ui": ["libs/shared-ui/src/index.ts"],
                    "@myorg/my-app": ["apps/my-app/src/index.ts"],
                }
            }
        }))

        ws = parse_nx_workspace(root)
        assert ws is not None
        assert ws["nx_version"] == "16.0.0"
        assert set(ws["projects"].keys()) == {"my-app", "shared-ui"}
        assert ws["projects"]["my-app"]["projectType"] == "application"
        assert ws["projects"]["shared-ui"]["projectType"] == "library"
        assert ws["tsconfig_paths"] == {
            "@myorg/shared-ui": "libs/shared-ui/src",
            "@myorg/my-app": "apps/my-app/src",
        }


def test_nx_framework_from_executor():
    targets = {"build": {"executor": "@nx/react:build"}}
    assert nx_framework_from_executor(targets) == "react"

    targets = {"build": {"executor": "@nx/angular:build"}}
    assert nx_framework_from_executor(targets) == "angular"

    targets = {"serve": {"executor": "@nx/nest:serve"}}
    assert nx_framework_from_executor(targets) == "nestjs"

    targets = {}
    assert nx_framework_from_executor(targets) is None


def test_build_nx_project_graph():
    ws = {
        "projects": {
            "app-a": {"root": "apps/app-a", "implicitDependencies": ["lib-b"]},
            "lib-b": {"root": "libs/lib-b", "implicitDependencies": []},
            "lib-c": {"root": "libs/lib-c", "implicitDependencies": ["lib-b"]},
        },
        "tsconfig_paths": {
            "@scope/lib-b": "libs/lib-b/src/index.ts",
            "@scope/lib-c": "libs/lib-c/src/index.ts",
        },
    }
    graph = build_nx_project_graph(ws)
    assert graph == {
        "app-a": ["lib-b"],
        "lib-b": [],
        "lib-c": ["lib-b"],
    }


def test_parse_tsconfig_paths():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "tsconfig.base.json").write_text(json.dumps({
            "compilerOptions": {
                "paths": {
                    "@scope/lib": ["libs/lib/src/index.ts"],
                    "@scope/lib/sub": ["libs/lib/src/sub/index.ts"],
                }
            }
        }))
        paths = _parse_tsconfig_paths(root)
        assert paths == {
            "@scope/lib": "libs/lib/src",
            "@scope/lib/sub": "libs/lib/src/sub",
        }


if __name__ == "__main__":
    test_parse_nx_workspace_no_nx_json()
    test_parse_nx_workspace_simple()
    test_nx_framework_from_executor()
    test_build_nx_project_graph()
    test_parse_tsconfig_paths()
    print("All Nx tests passed!")
