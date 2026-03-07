import fnmatch
from pathlib import Path
from typing import Callable


MatchesGitignore = Callable[[Path, Path], bool]


def should_ignore_file(
    file_path: Path,
    root: Path,
    default_ignore_patterns: list[str] | tuple[str, ...],
    exclude_patterns: set[str],
    include_patterns: list[str],
    include_tests: bool,
    matches_gitignore: MatchesGitignore,
) -> bool:
    path_str = str(file_path)
    rel_path = file_path.relative_to(root)
    rel_str = str(rel_path)
    path_posix = file_path.as_posix()
    rel_posix = rel_path.as_posix()

    for pattern in default_ignore_patterns:
        if pattern in path_str or pattern in path_posix or pattern in rel_posix:
            return True

    for pattern in exclude_patterns:
        normalized_pattern = pattern.replace("\\", "/")
        if (
            normalized_pattern in path_str
            or normalized_pattern in rel_str
            or normalized_pattern in path_posix
            or normalized_pattern in rel_posix
            or fnmatch.fnmatch(rel_posix, normalized_pattern)
            or fnmatch.fnmatch(path_posix, normalized_pattern)
        ):
            return True

    if include_patterns:
        matched = False
        for pattern in include_patterns:
            normalized_pattern = pattern.replace("\\", "/")
            if (
                fnmatch.fnmatch(rel_posix, normalized_pattern)
                or fnmatch.fnmatch(path_posix, normalized_pattern)
                or fnmatch.fnmatch(rel_posix, f"*/{normalized_pattern}")
                or fnmatch.fnmatch(rel_posix, f"**/{normalized_pattern}")
            ):
                matched = True
                break
        if not matched:
            return True

    if not include_tests:
        test_patterns = [
            ".test.", ".spec.", "__tests__", "test_", "_test.",
            "tests/", "test/", "spec/", "__spec__",
            ".test.js", ".test.ts", ".spec.js", ".spec.ts",
            "test.js", "test.ts", "spec.js", "spec.ts",
            ".test.jsx", ".test.tsx", ".spec.jsx", ".spec.tsx",
        ]
        for pattern in test_patterns:
            if pattern in path_str or pattern in path_posix or pattern in rel_posix:
                return True

    return matches_gitignore(file_path, root)


def is_file_too_large(file_path: Path, max_size: int) -> bool:
    try:
        return file_path.stat().st_size > max_size
    except OSError:
        return True
