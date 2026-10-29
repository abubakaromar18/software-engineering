"""Plain data types shared by detectors, the analyzer and the reporters.

Everything here is an immutable value object. Detectors produce ``Finding``s;
nothing downstream mutates them, which keeps reporters trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path


class Severity(IntEnum):
    """Ordered so that ``Severity.HIGH > Severity.LOW`` works for filtering."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @classmethod
    def parse(cls, text: str) -> Severity:
        try:
            return cls[text.strip().upper()]
        except KeyError:
            names = ", ".join(s.name.lower() for s in cls)
            raise ValueError(f"unknown severity {text!r} (expected one of: {names})") from None

    def __str__(self) -> str:
        return self.name.lower()


@dataclass(frozen=True, order=True)
class Location:
    """A span of lines in one file. Lines are 1-based and inclusive."""

    path: Path
    line: int
    end_line: int

    def __str__(self) -> str:
        if self.end_line != self.line:
            return f"{self.path}:{self.line}-{self.end_line}"
        return f"{self.path}:{self.line}"

    def contains(self, other: Location) -> bool:
        return (
            self.path == other.path and self.line <= other.line and other.end_line <= self.end_line
        )


@dataclass(frozen=True)
class Finding:
    """One detected smell.

    ``metric`` is what was measured and ``threshold`` is the configured limit it
    exceeded; the ``score`` (0-100) and ``severity`` are derived from the two so
    that every rule is ranked on the same scale.
    """

    rule: str
    location: Location
    message: str
    metric: int
    threshold: int
    score: int
    severity: Severity
    symbol: str | None = None
    related: tuple[Location, ...] = field(default_factory=tuple)

    def sort_key(self) -> tuple:
        return (-self.score, str(self.location.path), self.location.line, self.rule)


@dataclass(frozen=True)
class ParseError:
    """A file that could not be analysed. Reported, never fatal."""

    path: Path
    message: str


@dataclass(frozen=True)
class Report:
    """The result of one analysis run."""

    findings: tuple[Finding, ...]
    files_analyzed: int
    errors: tuple[ParseError, ...] = ()

    def at_or_above(self, severity: Severity) -> Report:
        kept = tuple(f for f in self.findings if f.severity >= severity)
        return Report(kept, self.files_analyzed, self.errors)

    def count_by_severity(self) -> dict[Severity, int]:
        counts = {s: 0 for s in Severity}
        for finding in self.findings:
            counts[finding.severity] += 1
        return counts
