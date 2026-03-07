from typing import Any


def detect_dead_code(index: dict) -> list[dict[str, Any]]:
    """Find symbols that are defined but never called by any other symbol.

    Returns a list of potentially dead symbols with their details.
    """
    call_graph = index.get("call_graph", {})
    files = index.get("files", {})

    all_called: set[str] = set()
    for callees in call_graph.values():
        all_called.update(callees)

    all_imported: set[str] = set()
    for file_data in files.values():
        if not isinstance(file_data, dict):
            continue
        for imp in file_data.get("imports", []):
            all_imported.update(imp.get("imported", []))

    all_referenced = all_called | all_imported

    dead: list[dict[str, Any]] = []
    for rel_path, file_data in files.items():
        if not isinstance(file_data, dict):
            continue
        for sym in file_data.get("symbols", []):
            name = sym.get("name", "")
            sym_type = sym.get("type", "")

            if _is_likely_entrypoint(name, sym, rel_path):
                continue

            if name not in all_referenced:
                dead.append({
                    "name": name,
                    "type": sym_type,
                    "file": rel_path,
                    "line": sym.get("line", 0),
                    "framework": sym.get("framework"),
                    "reason": "never called or imported by any other symbol",
                })

    return dead


def _is_likely_entrypoint(name: str, sym: dict, file_path: str) -> bool:
    """Check if a symbol is likely an entry point that won't appear in call graph."""
    framework = sym.get("framework") or ""
    if framework:
        return True

    entrypoint_names = {
        "main", "app", "init", "__init__", "setup", "configure", "register",
        "run", "start", "bootstrap", "index", "default", "handler",
    }
    if name.lower() in entrypoint_names:
        return True

    if sym.get("type") == "class":
        return True

    if "test" in file_path.lower() or "spec" in file_path.lower():
        return True

    lifecycle = {
        "componentDidMount", "componentWillUnmount", "render", "build",
        "ngOnInit", "ngOnDestroy", "viewDidLoad", "viewWillAppear",
        "onCreate", "onStart", "onResume", "onPause", "onStop", "onDestroy",
        "initState", "dispose", "didChangeDependencies",
    }
    if name in lifecycle:
        return True

    if name.startswith("__") and name.endswith("__"):
        return True

    if name.startswith("get_") or name.startswith("post_") or name.startswith("handle_"):
        return True

    return False
