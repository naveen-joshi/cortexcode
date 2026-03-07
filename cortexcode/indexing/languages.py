from tree_sitter import Parser

import tree_sitter_c_sharp
import tree_sitter_go
import tree_sitter_java
import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_rust
import tree_sitter_typescript

try:
    import tree_sitter_kotlin
    _HAS_KOTLIN = True
except ImportError:
    _HAS_KOTLIN = False

try:
    import tree_sitter_swift
    _HAS_SWIFT = True
except ImportError:
    _HAS_SWIFT = False


LANGUAGE_MAP: dict[str, tuple[str, object]] = {
    ".py": ("python", tree_sitter_python.language),
    ".js": ("javascript", tree_sitter_javascript.language),
    ".jsx": ("javascript", tree_sitter_javascript.language),
    ".ts": ("typescript", tree_sitter_typescript.language_tsx),
    ".tsx": ("typescript", tree_sitter_typescript.language_tsx),
    ".go": ("go", tree_sitter_go.language),
    ".rs": ("rust", tree_sitter_rust.language),
    ".java": ("java", tree_sitter_java.language),
    ".cs": ("csharp", tree_sitter_c_sharp.language),
}

if _HAS_KOTLIN:
    LANGUAGE_MAP[".kt"] = ("kotlin", tree_sitter_kotlin.language)
    LANGUAGE_MAP[".kts"] = ("kotlin", tree_sitter_kotlin.language)

if _HAS_SWIFT:
    LANGUAGE_MAP[".swift"] = ("swift", tree_sitter_swift.language)


REGEX_LANGUAGES = {
    ".dart": "dart",
}

SUPPORTED_EXTENSIONS = set(LANGUAGE_MAP.keys()) | set(REGEX_LANGUAGES.keys())
