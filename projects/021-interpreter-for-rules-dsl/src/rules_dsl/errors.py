"""Error hierarchy. Every stage raises a subclass of :class:`DslError`.

Catching ``DslError`` handles anything wrong with rules or facts; programming
errors in the host application (bugs) still surface as ordinary exceptions.
"""

from __future__ import annotations

from .source import Source, Span


class DslError(Exception):
    """Base class for all rules-language errors."""

    kind = "error"

    def __init__(self, message: str, span: Span | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.span = span

    def render(self, source: Source | None = None) -> str:
        """Format as ``file:line:col: kind: message`` with a source excerpt when possible."""
        if self.span is None:
            prefix = f"{source.name}: " if source else ""
            return f"{prefix}{self.kind}: {self.message}"
        name = source.name if source else "<input>"
        head = f"{name}:{self.span}: {self.kind}: {self.message}"
        return f"{head}\n{source.excerpt(self.span)}" if source else head


class LexError(DslError):
    kind = "syntax error"


class ParseError(DslError):
    kind = "syntax error"


class RulesetSyntaxError(DslError):
    """Several syntax errors collected by the parser's error recovery."""

    kind = "syntax errors"

    def __init__(self, errors: list[DslError]) -> None:
        super().__init__(f"{len(errors)} syntax error(s)")
        self.errors = errors

    def render(self, source: Source | None = None) -> str:
        return "\n".join(error.render(source) for error in self.errors)


class EvalError(DslError):
    """A rule failed at runtime: type mismatch, missing fact, division by zero..."""

    kind = "evaluation error"


class ConfigError(DslError):
    """The engine was configured or invoked incorrectly (not a problem in the rules text)."""

    kind = "configuration error"
