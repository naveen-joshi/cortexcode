from pathlib import Path


def load_gitignore_patterns(root: Path) -> list[tuple[str, bool]]:
    patterns: list[tuple[str, bool]] = []

    for gitignore_path in root.rglob('.gitignore'):
        try:
            gitignore_dir = gitignore_path.parent
            rel_dir = gitignore_dir.relative_to(root) if gitignore_dir != root else Path('.')

            for line in gitignore_path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                is_negation = line.startswith('!')
                pattern = line[1:].strip() if is_negation else line

                if pattern:
                    full_pattern = str(rel_dir / pattern) if rel_dir != Path('.') else pattern
                    patterns.append((full_pattern, is_negation))
        except (OSError, UnicodeDecodeError):
            continue

    return patterns


def match_pattern(pattern: str, parts: tuple[str, ...], rel_str: str) -> bool:
    pattern = pattern.rstrip('/')

    if '/' in pattern:
        pattern_parts = pattern.split('/')
        if pattern.startswith('/'):
            pattern_parts[0] = pattern_parts[0][1:]
            if parts[:len(pattern_parts)] == tuple(pattern_parts):
                return True
        else:
            for i in range(len(parts) - len(pattern_parts) + 1):
                if parts[i:i + len(pattern_parts)] == tuple(pattern_parts):
                    return True
    else:
        for part in parts:
            if part == pattern or (pattern.startswith('*') and part.endswith(pattern[1:])):
                return True

    if rel_str == pattern:
        return True

    return False


def matches_gitignore(file_path: Path, root: Path, patterns: list[tuple[str, bool]]) -> bool:
    try:
        rel_path = file_path.relative_to(root)
        rel_str = str(rel_path)
        parts = rel_path.parts

        for pattern, is_negation in patterns:
            if match_pattern(pattern, parts, rel_str):
                return not is_negation

        return False
    except ValueError:
        return True
