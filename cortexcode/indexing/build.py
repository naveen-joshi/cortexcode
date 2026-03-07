from pathlib import Path
from typing import Any


LanguageMap = dict[str, tuple[str, object]]
RegexLanguages = dict[str, str]


def build_index_result(
    root: Path,
    file_symbols: dict[str, Any],
    call_graph: dict[str, list[str]],
    timestamp: str,
    file_hashes: dict[str, str],
    build_file_dependencies_fn,
    build_type_map_fn,
    build_project_profile_fn,
    language_map: LanguageMap,
    regex_languages: RegexLanguages,
    plugin_registry,
) -> dict[str, Any]:
    languages = set()
    for file_path in file_symbols.keys():
        ext = Path(file_path).suffix.lower()
        lang_info = language_map.get(ext)
        if lang_info:
            languages.add(lang_info[0])
        elif ext in regex_languages:
            languages.add(regex_languages[ext])
        else:
            languages.add(ext.lstrip("."))

    file_deps = build_file_dependencies_fn()
    type_map = build_type_map_fn()
    project_profile = build_project_profile_fn(root, file_deps)

    result = {
        "project_root": str(root),
        "last_indexed": timestamp,
        "files": file_symbols,
        "call_graph": call_graph,
        "file_dependencies": file_deps,
        "file_hashes": file_hashes,
        "languages": list(languages),
        "project_profile": project_profile,
    }

    if type_map:
        result["type_map"] = type_map

    return plugin_registry.run_post_processors(result)
