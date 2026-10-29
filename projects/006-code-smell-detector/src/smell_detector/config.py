"""Thresholds and file selection, loaded from ``[tool.smell-detector]``.

Configuration is a frozen dataclass so detectors can't change it under each
other. Unknown keys and wrong types are rejected loudly: a typo such as
``max_function_line = 10`` silently doing nothing is worse than an error.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any

TOOL_TABLE = "smell-detector"


class ConfigError(Exception):
    """Raised for unreadable or invalid configuration."""


@dataclass(frozen=True)
class Config:
    max_function_lines: int = 50
    max_nesting_depth: int = 4
    max_class_methods: int = 20
    max_class_lines: int = 300
    duplicate_min_statements: int = 4
    duplicate_min_lines: int = 6
    exclude: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for f in fields(self):
            value = getattr(self, f.name)
            if f.type == "int" and (
                not isinstance(value, int) or isinstance(value, bool) or value < 1
            ):
                raise ConfigError(f"{f.name} must be a positive integer, got {value!r}")

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Config:
        known = {f.name for f in fields(cls)}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ConfigError(f"unknown option(s) in [tool.{TOOL_TABLE}]: {', '.join(unknown)}")
        values = dict(data)
        if "exclude" in values:
            exclude = values["exclude"]
            if not isinstance(exclude, list) or not all(isinstance(p, str) for p in exclude):
                raise ConfigError("exclude must be a list of glob strings")
            values["exclude"] = tuple(exclude)
        return cls(**values)

    @classmethod
    def from_pyproject(cls, path: Path) -> Config:
        """Load the tool table from a pyproject.toml. A missing table means defaults."""
        try:
            document = tomllib.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ConfigError(f"cannot read {path}: {exc.strerror}") from exc
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"invalid TOML in {path}: {exc}") from exc
        table = document.get("tool", {}).get(TOOL_TABLE, {})
        if not isinstance(table, dict):
            raise ConfigError(f"[tool.{TOOL_TABLE}] must be a table")
        return cls.from_mapping(table)

    @classmethod
    def discover(cls, start: Path) -> Config:
        """Walk up from ``start`` to the nearest pyproject.toml, like most Python tools."""
        directory = start.resolve()
        if directory.is_file():
            directory = directory.parent
        for candidate in (directory, *directory.parents):
            pyproject = candidate / "pyproject.toml"
            if pyproject.is_file():
                return cls.from_pyproject(pyproject)
        return cls()

    def with_overrides(self, **overrides: Any) -> Config:
        """Return a copy with the non-``None`` overrides applied (used by CLI flags)."""
        return replace(self, **{k: v for k, v in overrides.items() if v is not None})
