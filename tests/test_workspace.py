"""Tests for cortexcode.workspace — multi-repo workspace v1."""
import json
from pathlib import Path

import pytest
import yaml

from cortexcode.workspace import (
    Workspace,
    collect_manifest_dependencies,
    detect_package_name,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_repo(root: Path, name: str, package_name: str | None = None,
               deps: dict | None = None, index: dict | None = None) -> Path:
    """Create a repo dir with a package.json and an indexed `.cortexcode/index.json`."""
    repo = root / name
    repo.mkdir(parents=True)
    if package_name:
        manifest = {"name": package_name, "version": "1.0.0"}
        if deps:
            manifest["dependencies"] = deps
        (repo / "package.json").write_text(json.dumps(manifest))
    if index is not None:
        (repo / ".cortexcode").mkdir()
        (repo / ".cortexcode" / "index.json").write_text(json.dumps(index))
    return repo


def _make_pyproject_repo(root: Path, name: str, package_name: str,
                         deps: list[str] | None = None) -> Path:
    repo = root / name
    repo.mkdir(parents=True)
    deps_block = ""
    if deps:
        dep_lines = ",\n    ".join(f'"{d}"' for d in deps)
        deps_block = f"dependencies = [\n    {dep_lines}\n]\n"
    (repo / "pyproject.toml").write_text(
        f'[project]\nname = "{package_name}"\nversion = "0.1.0"\n{deps_block}'
    )
    return repo


# ── Package detection ─────────────────────────────────────────────────────────

def test_detect_package_name_from_package_json(tmp_path):
    repo = _make_repo(tmp_path, "frontend", package_name="@acme/frontend")
    assert detect_package_name(repo) == "@acme/frontend"


def test_detect_package_name_from_pyproject(tmp_path):
    repo = _make_pyproject_repo(tmp_path, "backend", "acme-backend")
    assert detect_package_name(repo) == "acme-backend"


def test_detect_package_name_missing(tmp_path):
    repo = tmp_path / "blank"
    repo.mkdir()
    assert detect_package_name(repo) is None


def test_collect_manifest_dependencies_npm(tmp_path):
    repo = _make_repo(
        tmp_path, "app", package_name="app",
        deps={"@acme/shared": "^1.0.0", "react": "^18"},
    )
    deps = collect_manifest_dependencies(repo)
    names = {n for n, _ in deps}
    assert "@acme/shared" in names
    assert "react" in names


def test_collect_manifest_dependencies_pyproject(tmp_path):
    repo = _make_pyproject_repo(
        tmp_path, "svc", "svc", deps=["click>=8.0", "acme-shared==1.0"],
    )
    deps = collect_manifest_dependencies(repo)
    names = {n for n, _ in deps}
    assert "click" in names
    assert "acme-shared" in names


# ── Config: load / save / discovery ───────────────────────────────────────────

def test_init_creates_yaml_config(tmp_path):
    ws = Workspace(tmp_path)
    ws.save_config()
    assert (tmp_path / "cortexcode-workspace.yml").exists()


def test_load_yaml_config(tmp_path):
    (tmp_path / "cortexcode-workspace.yml").write_text(yaml.safe_dump({
        "name": "acme",
        "repos": [
            {"id": "fe", "path": "./fe", "package": "@acme/fe"},
        ],
    }))
    ws = Workspace(tmp_path)
    assert ws.load_config()
    assert ws.name == "acme"
    assert len(ws.repos) == 1
    assert ws.repos[0]["id"] == "fe"
    assert ws.repos[0]["package"] == "@acme/fe"


def test_load_legacy_json_config(tmp_path):
    """Backward compat: old `.cortexcode-workspace.json` with `alias` key still loads."""
    (tmp_path / ".cortexcode-workspace.json").write_text(json.dumps({
        "repos": [{"alias": "fe", "path": str(tmp_path / "fe")}],
    }))
    ws = Workspace(tmp_path)
    assert ws.load_config()
    assert ws.repos[0]["id"] == "fe"
    assert ws.repos[0]["alias"] == "fe"


def test_discover_walks_parents(tmp_path):
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    (tmp_path / "cortexcode-workspace.yml").write_text(yaml.safe_dump({"name": "root", "repos": []}))
    ws = Workspace.discover(nested)
    assert ws is not None
    assert ws.name == "root"


def test_discover_returns_none_when_absent(tmp_path):
    assert Workspace.discover(tmp_path) is None


# ── Mutation: add / remove / list ─────────────────────────────────────────────

def test_add_repo_auto_detects_package(tmp_path):
    ws = Workspace(tmp_path)
    ws.save_config()
    repo = _make_repo(tmp_path, "frontend", package_name="@acme/frontend")
    added = ws.add_repo(str(repo))
    assert added["id"] == "frontend"
    assert added["package"] == "@acme/frontend"


def test_add_repo_rejects_duplicate_id(tmp_path):
    ws = Workspace(tmp_path)
    ws.save_config()
    repo1 = _make_repo(tmp_path, "frontend")
    repo2 = _make_repo(tmp_path, "frontend2")
    ws.add_repo(str(repo1), alias="fe")
    with pytest.raises(ValueError, match="id already in use"):
        ws.add_repo(str(repo2), alias="fe")


def test_add_repo_rejects_duplicate_path(tmp_path):
    ws = Workspace(tmp_path)
    ws.save_config()
    repo = _make_repo(tmp_path, "frontend")
    ws.add_repo(str(repo))
    with pytest.raises(ValueError, match="Already in workspace"):
        ws.add_repo(str(repo), alias="other")


def test_remove_repo_by_id(tmp_path):
    ws = Workspace(tmp_path)
    ws.save_config()
    repo = _make_repo(tmp_path, "frontend")
    ws.add_repo(str(repo), alias="fe")
    assert ws.remove_repo("fe")
    assert ws.list_repos() == []


def test_remove_repo_missing_returns_false(tmp_path):
    ws = Workspace(tmp_path)
    ws.save_config()
    assert not ws.remove_repo("nope")


def test_add_repo_stores_relative_path_for_portability(tmp_path):
    """Paths inside the workspace dir should be stored relative so the config is committable."""
    ws = Workspace(tmp_path)
    ws.save_config()
    repo = _make_repo(tmp_path, "frontend", package_name="@acme/frontend")
    ws.add_repo(str(repo))
    # Stored path should be relative to workspace root, not absolute.
    stored = ws.repos[0]["path"]
    assert stored == "frontend"
    # But list_repos should still report the absolute path for display.
    assert Path(ws.list_repos()[0]["path"]).is_absolute()


def test_relative_path_resolves_correctly_after_reload(tmp_path):
    """Workspace loaded from a relative-path config still finds the repos."""
    ws = Workspace(tmp_path)
    ws.save_config()
    _make_repo(tmp_path, "fe", package_name="fe", index={"files": {}})
    ws.add_repo(str(tmp_path / "fe"))

    reloaded = Workspace(tmp_path)
    assert reloaded.load_config()
    listed = reloaded.list_repos()
    assert listed[0]["indexed"] is True


def test_add_repo_outside_workspace_uses_absolute(tmp_path):
    """Repos outside the workspace dir keep absolute paths (relative_to would fail)."""
    ws_root = tmp_path / "workspace"
    ws_root.mkdir()
    sibling = tmp_path / "sibling"
    sibling.mkdir()
    (sibling / "package.json").write_text(json.dumps({"name": "sibling"}))

    ws = Workspace(ws_root)
    ws.save_config()
    ws.add_repo(str(sibling))
    assert Path(ws.repos[0]["path"]).is_absolute()


def test_list_repos_reports_indexed_status(tmp_path):
    ws = Workspace(tmp_path)
    ws.save_config()
    indexed = _make_repo(tmp_path, "fe", package_name="fe", index={"files": {}})
    not_indexed = _make_repo(tmp_path, "be", package_name="be")
    ws.add_repo(str(indexed))
    ws.add_repo(str(not_indexed))
    rows = {r["id"]: r for r in ws.list_repos()}
    assert rows["fe"]["indexed"] is True
    assert rows["be"]["indexed"] is False


# ── Linkage ───────────────────────────────────────────────────────────────────

def test_build_linkage_finds_package_edges(tmp_path):
    ws = Workspace(tmp_path)
    ws.save_config()
    shared = _make_repo(tmp_path, "shared", package_name="@acme/shared")
    frontend = _make_repo(
        tmp_path, "frontend",
        package_name="@acme/frontend",
        deps={"@acme/shared": "^1.0.0"},
    )
    ws.add_repo(str(shared))
    ws.add_repo(str(frontend))

    linkage = ws.build_linkage()
    edges = linkage["package_edges"]
    assert len(edges) == 1
    assert edges[0]["from_repo"] == "frontend"
    assert edges[0]["to_repo"] == "shared"
    assert edges[0]["package"] == "@acme/shared"


def test_build_linkage_ignores_external_deps(tmp_path):
    ws = Workspace(tmp_path)
    ws.save_config()
    fe = _make_repo(tmp_path, "fe", package_name="fe", deps={"react": "^18"})
    ws.add_repo(str(fe))
    linkage = ws.build_linkage()
    assert linkage["package_edges"] == []


def test_build_linkage_ignores_self_dep(tmp_path):
    ws = Workspace(tmp_path)
    ws.save_config()
    repo = _make_repo(tmp_path, "fe", package_name="fe", deps={"fe": "*"})
    ws.add_repo(str(repo))
    linkage = ws.build_linkage()
    assert linkage["package_edges"] == []


def test_build_linkage_dedups_dependencies_and_peer_dependencies(tmp_path):
    """Same package in both `dependencies` and `peerDependencies` should produce one edge."""
    ws = Workspace(tmp_path)
    ws.save_config()
    shared = _make_repo(tmp_path, "shared", package_name="@acme/shared")

    fe = tmp_path / "fe"
    fe.mkdir()
    (fe / "package.json").write_text(json.dumps({
        "name": "@acme/fe",
        "dependencies": {"@acme/shared": "^1.0.0"},
        "peerDependencies": {"@acme/shared": "^1.0.0"},
    }))
    ws.add_repo(str(shared))
    ws.add_repo(str(fe))

    linkage = ws.build_linkage()
    edges = [e for e in linkage["package_edges"] if e["from_repo"] == "fe"]
    assert len(edges) == 1, f"Expected 1 deduped edge, got {len(edges)}: {edges}"


def test_linkage_persisted_to_cache(tmp_path):
    ws = Workspace(tmp_path)
    ws.save_config()
    shared = _make_repo(tmp_path, "shared", package_name="@acme/shared")
    fe = _make_repo(tmp_path, "fe", package_name="fe", deps={"@acme/shared": "*"})
    ws.add_repo(str(shared))
    ws.add_repo(str(fe))
    ws.build_linkage()
    assert (tmp_path / ".cortexcode-workspace" / "linkage.json").exists()


def test_cross_repo_deps_graph(tmp_path):
    ws = Workspace(tmp_path)
    ws.save_config()
    shared = _make_repo(tmp_path, "shared", package_name="@acme/shared")
    fe = _make_repo(tmp_path, "fe", package_name="fe", deps={"@acme/shared": "*"})
    be = _make_repo(tmp_path, "be", package_name="be", deps={"@acme/shared": "*"})
    ws.add_repo(str(shared))
    ws.add_repo(str(fe))
    ws.add_repo(str(be))
    ws.build_linkage()

    deps = ws.cross_repo_deps()
    assert "shared" in deps["graph"]["fe"]
    assert "shared" in deps["graph"]["be"]
    assert deps["graph"]["shared"] == []


# ── Impact ────────────────────────────────────────────────────────────────────

def _setup_workspace_with_indexes(tmp_path):
    """Two repos: shared exports getUser; frontend imports it."""
    shared_index = {
        "files": {
            "src/api.ts": {
                "symbols": [
                    {"name": "getUser", "type": "function", "line": 1, "calls": []},
                    {"name": "deleteUser", "type": "function", "line": 10, "calls": []},
                ],
                "imports": [],
                "exports": ["getUser", "deleteUser"],
            }
        },
        "call_graph": {"deleteUser": ["getUser"]},
        "file_dependencies": {},
    }
    frontend_index = {
        "files": {
            "src/page.tsx": {
                "symbols": [
                    {"name": "Page", "type": "function", "line": 1, "calls": ["getUser"]},
                ],
                "imports": ["getUser from @acme/shared"],
            }
        },
        "call_graph": {"Page": ["getUser"]},
        "file_dependencies": {},
    }
    ws = Workspace(tmp_path)
    ws.save_config()
    shared = _make_repo(tmp_path, "shared", package_name="@acme/shared", index=shared_index)
    fe = _make_repo(
        tmp_path, "fe", package_name="@acme/fe",
        deps={"@acme/shared": "*"},
        index=frontend_index,
    )
    ws.add_repo(str(shared))
    ws.add_repo(str(fe))
    ws.build_linkage()
    return ws


def test_impact_local_callers(tmp_path):
    ws = _setup_workspace_with_indexes(tmp_path)
    result = ws.impact("shared:getUser")
    assert "deleteUser" in result["local"]["callers"]


def test_impact_cross_repo_finds_consumer(tmp_path):
    ws = _setup_workspace_with_indexes(tmp_path)
    result = ws.impact("shared:getUser")
    assert result["consumers"] == ["fe"]
    cross_repos = [c["repo"] for c in result["cross_repo"]]
    assert "fe" in cross_repos


def test_impact_unknown_repo(tmp_path):
    ws = _setup_workspace_with_indexes(tmp_path)
    result = ws.impact("ghost:foo")
    assert "error" in result
    assert "available_repos" in result


def test_impact_missing_repo_prefix_returns_helpful_error(tmp_path):
    ws = _setup_workspace_with_indexes(tmp_path)
    result = ws.impact("getUser")
    assert "error" in result
    assert "repo prefix" in result["error"].lower()
    assert "available_repos" in result


def test_impact_file_ref(tmp_path):
    ws = _setup_workspace_with_indexes(tmp_path)
    result = ws.impact("shared/src/api.ts")
    assert result["local"]["kind"] == "file"
    # No file dependencies in the test fixtures, so files_affected is empty —
    # but symbols_to_check should drive the cross-repo query and find the consumer.
    assert "fe" in result["consumers"]


# ── Federated search ──────────────────────────────────────────────────────────

def test_search_across_repos_returns_repo_label(tmp_path):
    ws = _setup_workspace_with_indexes(tmp_path)
    results = ws.search_across_repos("getUser")
    repos = {r["repo"] for r in results}
    assert "shared" in repos
    names = {r["name"] for r in results}
    assert "getUser" in names


def test_search_respects_limit(tmp_path):
    ws = _setup_workspace_with_indexes(tmp_path)
    results = ws.search_across_repos("e", max_results=2)  # broad match
    assert len(results) <= 2
