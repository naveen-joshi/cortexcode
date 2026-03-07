from pathlib import Path
from typing import Callable


ShouldIgnore = Callable[[Path, Path], bool]
IsFileTooLarge = Callable[[Path, int], bool]
ReuseUnchangedFile = Callable[[Path], bool]
IndexFile = Callable[[Path, Path], None]


def walk_and_index_files(
    root_path: Path,
    extensions: set[str],
    should_ignore: ShouldIgnore,
    is_file_too_large: IsFileTooLarge,
    max_file_size: int,
    incremental: bool,
    reuse_unchanged_file: ReuseUnchangedFile,
    index_file: IndexFile,
) -> None:
    for ext in extensions:
        for file_path in root_path.rglob(f"*{ext}"):
            if should_ignore(file_path, root_path):
                continue

            if is_file_too_large(file_path, max_file_size):
                continue

            if incremental and reuse_unchanged_file(file_path):
                continue

            index_file(file_path, root_path)
