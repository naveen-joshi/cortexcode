from pathlib import PurePosixPath
from typing import Any


def normalize_module_key(key: str) -> str:
    normalized = str(key).replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.rstrip("/")


def build_exports_by_file(file_symbols: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    exports_by_file: dict[str, dict[str, dict[str, Any]]] = {}

    for rel_path, file_data in file_symbols.items():
        if not isinstance(file_data, dict):
            continue

        file_exports: dict[str, dict[str, Any]] = {}
        for sym in file_data.get("symbols", []):
            name = sym.get("name")
            if name and not sym.get("class"):
                file_exports[name] = {
                    "defined_in": rel_path,
                    "type": sym.get("type"),
                    "line": sym.get("line"),
                }

        for exp in file_data.get("exports", []):
            name = exp.get("name")
            if name and name not in file_exports:
                file_exports[name] = {
                    "defined_in": rel_path,
                    "type": exp.get("type", "export"),
                    "line": exp.get("line"),
                }

        exports_by_file[rel_path] = file_exports

    return exports_by_file


def build_module_lookup(file_symbols: dict[str, Any]) -> dict[str, set[str]]:
    module_lookup: dict[str, set[str]] = {}

    for rel_path in file_symbols:
        normalized_rel = normalize_module_key(rel_path)
        rel_obj = PurePosixPath(normalized_rel)
        no_ext = normalize_module_key(str(rel_obj.with_suffix("")))
        keys = {
            normalized_rel,
            no_ext,
            no_ext.replace("/", "."),
            rel_obj.stem,
        }

        if rel_obj.name == "__init__.py":
            package_key = normalize_module_key(str(rel_obj.parent))
            if package_key and package_key != ".":
                keys.add(package_key)
                keys.add(package_key.replace("/", "."))

        if rel_obj.stem == "index":
            parent_key = normalize_module_key(str(rel_obj.parent))
            if parent_key and parent_key != ".":
                keys.add(parent_key)
                keys.add(parent_key.replace("/", "."))

        for key in keys:
            normalized_key = normalize_module_key(key)
            if normalized_key:
                module_lookup.setdefault(normalized_key, set()).add(normalized_rel)

    return module_lookup


def candidate_module_keys(rel_path: str, imp: dict[str, Any]) -> list[str]:
    module = str(imp.get("module", "")).strip()
    imported_names = [name for name in imp.get("imported", []) if name and name != "*"]
    if not module:
        return []

    normalized_rel = normalize_module_key(rel_path)
    current_dir = PurePosixPath(normalized_rel).parent
    candidates: list[str] = []

    if module.startswith("."):
        dot_prefix = len(module) - len(module.lstrip("."))
        remainder = module[dot_prefix:]
        base_dir = current_dir
        for _ in range(max(dot_prefix - 1, 0)):
            base_dir = base_dir.parent

        base_candidate = base_dir
        if remainder:
            base_candidate = base_dir / PurePosixPath(remainder.replace(".", "/"))

        candidates.append(str(base_candidate))
        for imported_name in imported_names:
            candidates.append(str(base_candidate / imported_name.replace(".", "/")))
    else:
        cleaned = module.replace("@/", "src/").replace("~/", "")
        candidates.append(cleaned)
        if "/" not in cleaned and "." in cleaned:
            candidates.append(cleaned.replace(".", "/"))
        for imported_name in imported_names:
            candidates.append(f"{cleaned}/{imported_name.replace('.', '/')}")

    return candidates


def resolve_import_to_files(
    rel_path: str,
    imp: dict[str, Any],
    module_lookup: dict[str, set[str]],
) -> list[str]:
    resolved_files = set()
    for candidate in candidate_module_keys(rel_path, imp):
        normalized_candidate = normalize_module_key(candidate)
        if not normalized_candidate:
            continue

        if normalized_candidate in module_lookup:
            resolved_files.update(module_lookup[normalized_candidate])

        dotted_candidate = normalized_candidate.replace("/", ".")
        if dotted_candidate in module_lookup:
            resolved_files.update(module_lookup[dotted_candidate])

    normalized_rel = normalize_module_key(rel_path)
    return sorted(file_path for file_path in resolved_files if file_path != normalized_rel)


def build_type_map(file_symbols: dict[str, Any]) -> dict[str, dict[str, Any]]:
    exports_by_file = build_exports_by_file(file_symbols)
    module_lookup = build_module_lookup(file_symbols)

    type_map: dict[str, dict[str, Any]] = {}
    for rel_path, file_data in file_symbols.items():
        if not isinstance(file_data, dict):
            continue

        for imp in file_data.get("imports", []):
            imported_names = imp.get("imported", [])
            target_files = resolve_import_to_files(rel_path, imp, module_lookup)
            if not target_files:
                continue

            for target_file in target_files:
                target_exports = exports_by_file.get(target_file, {})
                if not target_exports:
                    continue

                names_to_map = target_exports.keys() if "*" in imported_names else imported_names
                for imported_name in names_to_map:
                    if imported_name not in target_exports:
                        continue
                    defn = target_exports[imported_name]
                    if defn["defined_in"] == rel_path:
                        continue
                    key = f"{rel_path}:{imported_name}"
                    type_map[key] = {
                        "imported_in": rel_path,
                        "name": imported_name,
                        "defined_in": defn["defined_in"],
                        "type": defn.get("type"),
                        "line": defn.get("line"),
                    }

    return type_map


def build_file_dependencies(file_symbols: dict[str, Any]) -> dict[str, list[str]]:
    deps = {}
    module_lookup = build_module_lookup(file_symbols)

    for rel_path, file_data in file_symbols.items():
        if not isinstance(file_data, dict):
            continue
        imports = file_data.get("imports", [])
        if not imports:
            continue

        dep_files = set()
        for imp in imports:
            dep_files.update(resolve_import_to_files(rel_path, imp, module_lookup))

        if dep_files:
            deps[rel_path] = sorted(dep_files)

    return deps
