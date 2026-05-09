"""Multi-repo workspace support — index and query across multiple repositories.

A workspace groups several repos that belong to the same logical project but
live in separate directories (e.g. an `acme-frontend` / `acme-backend` /
`acme-shared` trio). It provides cross-repo search, impact analysis, and a
package-level dependency graph between members.

Layout (v1):
    <workspace-root>/
        cortexcode-workspace.yml         ← committed config (preferred)
        cortexcode-workspace.json        ← legacy JSON config (still loaded)
        .cortexcode-workspace/
            linkage.json                 ← cache of cross-repo edges (gitignored)

Each member repo continues to maintain its own `.cortexcode/index.json`. The
workspace builds a separate linkage layer over them; per-repo indexes are
never merged.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from cortexcode.indexer import CodeIndexer


# ── Constants ─────────────────────────────────────────────────────────────────

YAML_CONFIG = "cortexcode-workspace.yml"
JSON_CONFIG_LEGACY = ".cortexcode-workspace.json"
JSON_CONFIG_NEW = "cortexcode-workspace.json"
CACHE_DIR = ".cortexcode-workspace"
LINKAGE_FILE = "linkage.json"


# ── Workspace ─────────────────────────────────────────────────────────────────

class Workspace:
    """Manage multiple repositories as a single workspace."""

    # Kept for backward compat with the previous on-disk format and tests.
    CONFIG_FILE = JSON_CONFIG_LEGACY

    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.name: str = self.workspace_root.name
        self.repos: list[dict[str, Any]] = []
        self.merged_index: dict[str, Any] = {}
        self._config_path: Path | None = None  # set on load/save

    # ── Discovery ──────────────────────────────────────────────────────────

    @classmethod
    def discover(cls, start: Path | None = None) -> "Workspace | None":
        """Walk parent directories looking for a workspace config. Return None if not found."""
        cur = (start or Path.cwd()).resolve()
        for candidate in (cur, *cur.parents):
            for filename in (YAML_CONFIG, JSON_CONFIG_NEW, JSON_CONFIG_LEGACY):
                if (candidate / filename).exists():
                    ws = cls(candidate)
                    if ws.load_config():
                        return ws
        return None

    # ── Config I/O ─────────────────────────────────────────────────────────

    def load_config(self) -> bool:
        """Load workspace config. Tries YAML first, then JSON variants."""
        for filename in (YAML_CONFIG, JSON_CONFIG_NEW, JSON_CONFIG_LEGACY):
            path = self.workspace_root / filename
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8")
                data = yaml.safe_load(text) if filename.endswith(".yml") else json.loads(text)
            except (yaml.YAMLError, json.JSONDecodeError, OSError):
                return False
            if not isinstance(data, dict):
                return False
            self.name = data.get("name") or self.workspace_root.name
            self.repos = [self._normalize_repo(r) for r in data.get("repos", []) if isinstance(r, dict)]
            self._config_path = path
            return True
        return False

    def save_config(self) -> None:
        """Save workspace config. Preserves the current format; defaults to YAML for new workspaces."""
        path = self._config_path or (self.workspace_root / YAML_CONFIG)
        data = {
            "name": self.name,
            "repos": [self._serialize_repo(r) for r in self.repos],
        }
        if path.suffix == ".yml":
            path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        else:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._config_path = path

    @staticmethod
    def _normalize_repo(raw: dict) -> dict:
        """Normalize a raw repo entry to the canonical {id, path, package} form."""
        repo: dict[str, Any] = {}
        repo["id"] = raw.get("id") or raw.get("alias") or Path(raw.get("path", "")).name
        repo["alias"] = repo["id"]  # legacy alias mirror for back-compat
        repo["path"] = raw.get("path", "")
        if "package" in raw:
            repo["package"] = raw["package"]
        return repo

    @staticmethod
    def _serialize_repo(repo: dict) -> dict:
        """Serialize a normalized repo back to disk form (drops alias mirror if id is set)."""
        out = {"id": repo["id"], "path": repo["path"]}
        if repo.get("package"):
            out["package"] = repo["package"]
        return out

    # ── Mutation ────────────────────────────────────────────────────────────

    def add_repo(self, path: str, alias: str | None = None) -> dict:
        """Add a repository to the workspace.

        `alias` is kept as a parameter name for back-compat — it sets the repo `id`.
        Paths are stored relative to the workspace root when possible, so the
        config remains portable when committed to git.
        """
        repo_path = Path(path).resolve()
        if not repo_path.is_dir():
            raise ValueError(f"Not a directory: {repo_path}")

        for r in self.repos:
            if self._repo_abs_path(r) == repo_path:
                raise ValueError(f"Already in workspace: {repo_path}")

        repo_id = alias or repo_path.name
        if any(r["id"] == repo_id for r in self.repos):
            raise ValueError(f"Repo id already in use: {repo_id}")

        repo = {
            "id": repo_id,
            "alias": repo_id,
            "path": self._store_path(repo_path),
        }
        package = detect_package_name(repo_path)
        if package:
            repo["package"] = package

        self.repos.append(repo)
        self.save_config()
        return repo

    def _store_path(self, repo_path: Path) -> str:
        """Store repo path relative to workspace root when possible (portable for git)."""
        try:
            return str(repo_path.relative_to(self.workspace_root))
        except ValueError:
            return str(repo_path)

    def _repo_abs_path(self, repo: dict) -> Path:
        """Resolve a stored repo path (which may be relative) to an absolute Path."""
        p = Path(repo["path"])
        if p.is_absolute():
            return p
        return (self.workspace_root / p).resolve()

    def remove_repo(self, alias_or_path: str) -> bool:
        """Remove a repository by id, alias, or path."""
        resolved = Path(alias_or_path).resolve()

        for i, r in enumerate(self.repos):
            if r["id"] == alias_or_path or r.get("alias") == alias_or_path:
                self.repos.pop(i)
                self.save_config()
                return True
            if self._repo_abs_path(r) == resolved:
                self.repos.pop(i)
                self.save_config()
                return True
        return False

    def list_repos(self) -> list[dict]:
        """List all repos with their indexed status."""
        out = []
        for r in self.repos:
            abs_path = self._repo_abs_path(r)
            out.append({
                "id": r["id"],
                "alias": r.get("alias", r["id"]),
                "path": str(abs_path),
                "package": r.get("package"),
                "indexed": (abs_path / ".cortexcode" / "index.json").exists(),
            })
        return out

    def get_repo(self, repo_id: str) -> dict | None:
        for r in self.repos:
            if r["id"] == repo_id or r.get("alias") == repo_id:
                return r
        return None

    # ── Indexing ────────────────────────────────────────────────────────────

    def index_all(self, incremental: bool = True) -> dict[str, int]:
        """Index every member repo. Returns {repo_id: symbol_count} (-1 on failure)."""
        results: dict[str, int] = {}
        for r in self.repos:
            repo_path = self._repo_abs_path(r)
            if not repo_path.is_dir():
                results[r["id"]] = -1
                continue

            idx = CodeIndexer()
            index = idx.index_directory(repo_path, incremental=incremental)

            output_dir = repo_path / ".cortexcode"
            output_dir.mkdir(exist_ok=True)
            (output_dir / "index.json").write_text(
                json.dumps(index, indent=2, default=str), encoding="utf-8"
            )

            results[r["id"]] = _count_symbols(index)

        # Always rebuild linkage after re-indexing.
        self.build_linkage()
        return results

    # ── Per-repo index access ───────────────────────────────────────────────

    def _load_repo_index(self, repo_id: str) -> dict | None:
        repo = self.get_repo(repo_id)
        if not repo:
            return None
        index_path = self._repo_abs_path(repo) / ".cortexcode" / "index.json"
        if not index_path.exists():
            return None
        try:
            return json.loads(index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    # ── Merged view (legacy — kept for back-compat) ─────────────────────────

    def get_merged_index(self) -> dict[str, Any]:
        """Build an in-memory merged view across repos.

        v1 prefers federated queries (per-repo dispatch) but this remains for
        legacy callers like `search_across_repos`.
        """
        merged_files: dict[str, Any] = {}
        merged_call_graph: dict[str, list[str]] = {}
        merged_symbols: list[dict] = []
        merged_file_deps: dict[str, list[str]] = {}
        languages: set[str] = set()

        for r in self.repos:
            index = self._load_repo_index(r["id"])
            if not index:
                continue
            rid = r["id"]

            for rel_path, file_data in index.get("files", {}).items():
                merged_files[f"{rid}/{rel_path}"] = file_data
                if isinstance(file_data, dict):
                    for sym in file_data.get("symbols", []):
                        sym_copy = dict(sym)
                        sym_copy["file"] = f"{rid}/{rel_path}"
                        sym_copy["repo"] = rid
                        merged_symbols.append(sym_copy)

            for caller, callees in index.get("call_graph", {}).items():
                merged_call_graph[f"{rid}:{caller}"] = [f"{rid}:{c}" for c in callees]

            for f, deps in index.get("file_dependencies", {}).items():
                merged_file_deps[f"{rid}/{f}"] = [f"{rid}/{d}" for d in deps]

            languages.update(index.get("languages", []))

        self.merged_index = {
            "files": merged_files,
            "call_graph": merged_call_graph,
            "symbols": merged_symbols,
            "file_dependencies": merged_file_deps,
            "languages": sorted(languages),
            "project_root": str(self.workspace_root),
            "repos": [r["id"] for r in self.repos],
        }
        return self.merged_index

    def search_across_repos(self, query: str, max_results: int = 20) -> list[dict]:
        """Substring search across all repos. Federated — no merged-index dependency."""
        query_lower = query.lower()
        results: list[dict] = []
        for r in self.repos:
            index = self._load_repo_index(r["id"])
            if not index:
                continue
            for rel_path, file_data in index.get("files", {}).items():
                if not isinstance(file_data, dict):
                    continue
                for sym in file_data.get("symbols", []):
                    name = sym.get("name", "")
                    if query_lower in name.lower():
                        results.append({
                            "repo": r["id"],
                            "name": name,
                            "type": sym.get("type"),
                            "file": rel_path,
                            "line": sym.get("line"),
                        })
                        if len(results) >= max_results:
                            return results
        return results

    # ── Linkage ────────────────────────────────────────────────────────────

    def linkage_path(self) -> Path:
        return self.workspace_root / CACHE_DIR / LINKAGE_FILE

    def build_linkage(self) -> dict[str, Any]:
        """Build the cross-repo linkage layer.

        v1 produces only package-edges: when repo A's manifest declares a
        dependency whose name matches repo B's `package`, an edge is recorded.
        """
        members_by_pkg: dict[str, str] = {
            r["package"]: r["id"] for r in self.repos if r.get("package")
        }

        edges: list[dict[str, Any]] = []
        seen_edges: set[tuple[str, str, str]] = set()
        for r in self.repos:
            repo_path = self._repo_abs_path(r)
            if not repo_path.is_dir():
                continue
            for dep_name, manifest in collect_manifest_dependencies(repo_path):
                target = members_by_pkg.get(dep_name)
                if not target or target == r["id"]:
                    continue
                # Dedup: same package listed in dependencies + peerDependencies should
                # only emit one edge.
                key = (r["id"], target, dep_name)
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                edges.append({
                    "from_repo": r["id"],
                    "to_repo": target,
                    "package": dep_name,
                    "via": "package",
                    "manifest": manifest,
                })

        linkage = {
            "workspace": self.name,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "repos": [{"id": r["id"], "package": r.get("package")} for r in self.repos],
            "package_edges": edges,
        }

        cache_dir = self.workspace_root / CACHE_DIR
        cache_dir.mkdir(exist_ok=True)
        self.linkage_path().write_text(json.dumps(linkage, indent=2), encoding="utf-8")
        return linkage

    def load_linkage(self) -> dict[str, Any] | None:
        path = self.linkage_path()
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def cross_repo_deps(self) -> dict[str, Any]:
        """Return the cross-repo dep graph as adjacency lists, building linkage if missing."""
        linkage = self.load_linkage() or self.build_linkage()
        graph: dict[str, list[str]] = {r["id"]: [] for r in self.repos}
        for edge in linkage.get("package_edges", []):
            src, dst = edge["from_repo"], edge["to_repo"]
            if dst not in graph.get(src, []):
                graph.setdefault(src, []).append(dst)
        return {
            "workspace": self.name,
            "graph": graph,
            "edges": linkage.get("package_edges", []),
        }

    # ── Impact ─────────────────────────────────────────────────────────────

    def impact(self, ref: str) -> dict[str, Any]:
        """Cross-repo impact analysis.

        `ref` is `<repo_id>:<symbol>` or `<repo_id>/<file>` or just `<repo_id>:<symbol>`.
        Returns local callers (call graph) plus heuristic cross-repo references.
        """
        repo_id, target = _parse_ref(ref)
        if not repo_id:
            return {
                "error": "Workspace impact requires a repo prefix. "
                         "Use '<repo_id>:<symbol>' or '<repo_id>/<file>'.",
                "ref": ref,
                "available_repos": [r["id"] for r in self.repos],
            }
        repo = self.get_repo(repo_id)
        if not repo:
            return {
                "error": f"Unknown repo: {repo_id!r}",
                "ref": ref,
                "available_repos": [r["id"] for r in self.repos],
            }

        index = self._load_repo_index(repo["id"])
        if not index:
            return {"error": f"Repo {repo['id']!r} is not indexed — run `workspace index`"}

        is_file = "/" in target or target.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".cs", ".rs"))

        local: dict[str, Any] = {
            "repo": repo["id"],
            "target": target,
            "kind": "file" if is_file else "symbol",
            "callers": [],
            "files_affected": [],
        }
        symbols_to_check: list[str] = []

        if is_file:
            file_data = index.get("files", {}).get(target)
            if not file_data:
                return {"error": f"File not found in {repo['id']}: {target}"}
            symbols_to_check = [s.get("name") for s in file_data.get("symbols", []) if s.get("name")]
            local["files_affected"] = sorted({
                f for f, deps in index.get("file_dependencies", {}).items() if target in deps
            })
        else:
            symbols_to_check = [target]
            call_graph = index.get("call_graph", {})
            local["callers"] = sorted({
                caller for caller, callees in call_graph.items() if target in callees
            })

        # Cross-repo: traverse linkage edges where another repo depends on this one.
        cross: list[dict[str, Any]] = []
        deps = self.cross_repo_deps()["graph"]
        consumers = [src for src, targets in deps.items() if repo["id"] in targets]

        for consumer_id in consumers:
            consumer_index = self._load_repo_index(consumer_id)
            if not consumer_index:
                continue
            hits = _scan_symbol_references(consumer_index, symbols_to_check)
            if hits:
                cross.append({"repo": consumer_id, "hits": hits[:50], "hit_count": len(hits)})

        return {
            "ref": ref,
            "local": local,
            "cross_repo": cross,
            "consumers": consumers,
        }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _count_symbols(index: dict) -> int:
    """Robust symbol count whether the indexer returns a flat list or a per-file map."""
    if "symbols" in index and isinstance(index["symbols"], list):
        return len(index["symbols"])
    total = 0
    for file_data in index.get("files", {}).values():
        if isinstance(file_data, dict):
            total += len(file_data.get("symbols", []))
    return total


def _parse_ref(ref: str) -> tuple[str, str]:
    """Split a workspace ref `<repo>:<target>` or `<repo>/<file>`. Returns ("", ref) if no separator."""
    if ":" in ref:
        repo, _, target = ref.partition(":")
        return repo, target
    if "/" in ref:
        repo, _, target = ref.partition("/")
        return repo, target
    return "", ref


def _scan_symbol_references(index: dict, symbols: list[str]) -> list[dict]:
    """Heuristic: find files in `index` that mention any of `symbols`.

    Looks at imports (exact match) and the consumer's own symbol calls
    (call_graph entries where one of `symbols` appears as a callee).
    Both are weak signals individually but high-precision when paired with
    a known package edge between the two repos.
    """
    hits: list[dict] = []
    sym_set = {s for s in symbols if s}
    if not sym_set:
        return hits

    files = index.get("files", {})
    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue
        imports = file_data.get("imports", []) or []
        matched_imports = [imp for imp in imports if any(s in str(imp) for s in sym_set)]
        matched_calls: list[str] = []
        for sym in file_data.get("symbols", []):
            for callee in sym.get("calls", []) or []:
                if callee in sym_set:
                    matched_calls.append(f"{sym.get('name')} -> {callee}")
        if matched_imports or matched_calls:
            hits.append({
                "file": rel_path,
                "imports": matched_imports[:10],
                "calls": matched_calls[:10],
            })
    return hits


# ── Manifest parsing for package detection / dep collection ───────────────────

def detect_package_name(repo_path: Path) -> str | None:
    """Best-effort package-name detection from common manifests."""
    pkg_json = repo_path / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            name = data.get("name")
            if name:
                return name
        except (json.JSONDecodeError, OSError):
            pass

    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8")
        except OSError:
            content = ""
        m = re.search(r'^\s*name\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if m:
            return m.group(1)

    setup_py = repo_path / "setup.py"
    if setup_py.exists():
        try:
            content = setup_py.read_text(encoding="utf-8")
        except OSError:
            content = ""
        m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        if m:
            return m.group(1)

    cargo = repo_path / "Cargo.toml"
    if cargo.exists():
        try:
            content = cargo.read_text(encoding="utf-8")
        except OSError:
            content = ""
        m = re.search(r'^\s*name\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if m:
            return m.group(1)

    go_mod = repo_path / "go.mod"
    if go_mod.exists():
        try:
            content = go_mod.read_text(encoding="utf-8")
        except OSError:
            content = ""
        m = re.search(r'^\s*module\s+(\S+)', content, re.MULTILINE)
        if m:
            return m.group(1)

    return None


def collect_manifest_dependencies(repo_path: Path) -> list[tuple[str, str]]:
    """Yield (dep_name, manifest_filename) tuples for every direct dep declared by the repo."""
    out: list[tuple[str, str]] = []

    pkg_json = repo_path / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            for section in ("dependencies", "devDependencies", "peerDependencies"):
                for name in (data.get(section) or {}):
                    out.append((name, "package.json"))
        except (json.JSONDecodeError, OSError):
            pass

    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8")
        except OSError:
            content = ""
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("dependencies") and "=" in stripped:
                in_deps = True
                continue
            if in_deps:
                if stripped == "]":
                    in_deps = False
                    continue
                m = re.search(r'"([a-zA-Z0-9_\-./@]+)', stripped)
                if m:
                    out.append((m.group(1), "pyproject.toml"))

    requirements = repo_path / "requirements.txt"
    if requirements.exists():
        try:
            for line in requirements.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith(("#", "-")):
                    continue
                m = re.match(r'^([a-zA-Z0-9_\-.]+)', line)
                if m:
                    out.append((m.group(1), "requirements.txt"))
        except OSError:
            pass

    cargo = repo_path / "Cargo.toml"
    if cargo.exists():
        try:
            content = cargo.read_text(encoding="utf-8")
        except OSError:
            content = ""
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped == "[dependencies]":
                in_deps = True
                continue
            if stripped.startswith("["):
                in_deps = False
                continue
            if in_deps and "=" in stripped:
                name = stripped.split("=", 1)[0].strip()
                if name:
                    out.append((name, "Cargo.toml"))

    go_mod = repo_path / "go.mod"
    if go_mod.exists():
        try:
            content = go_mod.read_text(encoding="utf-8")
        except OSError:
            content = ""
        in_require = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("require ("):
                in_require = True
                continue
            if in_require and stripped == ")":
                in_require = False
                continue
            if in_require:
                parts = stripped.split()
                if parts and "/" in parts[0]:
                    out.append((parts[0], "go.mod"))
            elif stripped.startswith("require ") and len(stripped.split()) >= 3:
                out.append((stripped.split()[1], "go.mod"))

    return out
