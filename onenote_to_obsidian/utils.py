"""Filesystem helpers: filename sanitization, path utilities."""

import re
import unicodedata
from pathlib import Path


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """Convert a page/section/notebook title to a safe filename.

    Replaces filesystem-illegal characters, collapses whitespace,
    strips leading dots, and truncates to max_length.
    """
    name = unicodedata.normalize("NFC", name)
    name = re.sub(r'[/\\:*?"<>|]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.lstrip(".")
    if len(name) > max_length:
        name = name[:max_length].rstrip()
    return name or "Untitled"


def deduplicate_path(path: Path, existing_paths: set[Path] | None = None) -> Path:
    """If path stem already used, append _1, _2, etc.

    Args:
        path: pathlib.Path to check
        existing_paths: optional set of already-used paths to check against.
                        If None, checks filesystem.
    """
    if existing_paths is not None:
        if path not in existing_paths:
            return path
    elif not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if existing_paths is not None:
            if candidate not in existing_paths:
                return candidate
        elif not candidate.exists():
            return candidate
        counter += 1
