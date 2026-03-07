from typing import Any

from tree_sitter import Language, Parser


def get_parser_for_extension(ext: str, parsers: dict[str, Parser], language_map: dict[str, tuple[str, Any]]) -> Parser | None:
    if ext in parsers:
        return parsers[ext]

    if ext not in language_map:
        return None

    try:
        lang_func = language_map[ext][1]
        parser = Parser(Language(lang_func()))
        parsers[ext] = parser
        return parser
    except Exception as exc:
        print(f"Failed to load parser for {ext}: {exc}")
        return None
