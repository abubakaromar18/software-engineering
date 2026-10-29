"""Expand command-line paths into the Python files to analyse."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from fnmatch import fnmatch
from pathlib import Path, PurePath

# Directories that never contain first-party source worth scanning.
SKIPPED_DIRS = frozenset(
    {".git", ".hg", ".venv", "venv", "__pycache__", ".tox", ".nox", "build", "dist", "node_modules"}
)


def find_python_files(paths: Iterable[Path], exclude: Iterable[str] = ()) -> Iterator[Path]:
    """Yield ``.py`` files under ``paths`` in a deterministic order.

    Files named explicitly are always included. Files found by walking a
    directory are skipped if they match an ``exclude`` glob (matched against
    the POSIX path relative to that directory; ``*`` also crosses ``/``) or
    sit in a ``SKIPPED_DIRS`` folder.
    """
    patterns = tuple(exclude)
    seen: set[Path] = set()
    for root in paths:
        if root.is_file():
            candidates: Iterable[tuple[Path, PurePath]] = [(root, PurePath(root.name))]
        elif root.is_dir():
            candidates = (
                (path, path.relative_to(root))
                for path in sorted(root.rglob("*.py"))
                if not SKIPPED_DIRS.intersection(path.relative_to(root).parts[:-1])
            )
        else:
            raise FileNotFoundError(f"no such file or directory: {root}")
        for path, relative in candidates:
            if root.is_dir() and any(fnmatch(relative.as_posix(), p) for p in patterns):
                continue
            key = path.resolve()
            if key not in seen:
                seen.add(key)
                yield path
