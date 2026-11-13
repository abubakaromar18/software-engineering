"""Source text and locations, shared by every stage of the pipeline.

Each token and AST node carries a :class:`Span`, so an error raised while lexing,
parsing, checking or evaluating can point at the exact text that caused it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Span:
    """A half-open range ``[start, end)`` of character offsets, plus the start's line/column."""

    start: int
    end: int
    line: int
    column: int

    def to(self, other: Span) -> Span:
        """Return the span covering ``self`` through ``other``."""
        return Span(self.start, max(self.end, other.end), self.line, self.column)

    def __str__(self) -> str:
        return f"{self.line}:{self.column}"


@dataclass(frozen=True, slots=True)
class Source:
    """A named piece of rules text."""

    text: str
    name: str = "<input>"

    def line_text(self, line: int) -> str:
        lines = self.text.splitlines()
        return lines[line - 1] if 0 < line <= len(lines) else ""

    def excerpt(self, span: Span) -> str:
        """Render the offending line with a caret underline, compiler style."""
        text = self.line_text(span.line)
        line_end = span.start - (span.column - 1) + len(text)
        width = max(1, min(span.end, line_end) - span.start)
        gutter = f"{span.line:>4} | "
        underline = " " * (len(gutter) + span.column - 1) + "^" * width
        return f"{gutter}{text}\n{underline}"
