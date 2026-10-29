"""Long Method: functions whose body has too many lines of code.

Length is measured in *code lines*: physical lines that hold at least one
token, excluding blank lines, comment-only lines and the docstring. This
rewards documentation instead of penalising it, and a function that is long
only because it is well commented is not flagged.

Nested functions count toward their parent's length (they are physically part
of it) and are also measured on their own.
"""

from __future__ import annotations

from collections.abc import Iterator

from smell_detector.detectors.base import iter_functions, make_finding, span
from smell_detector.models import Finding
from smell_detector.source import SourceFile, docstring_lines


class LongMethodDetector:
    rule = "long-method"

    def __init__(self, max_lines: int) -> None:
        self.max_lines = max_lines

    def check(self, source: SourceFile) -> Iterator[Finding]:
        for func, qualname in iter_functions(source.tree):
            location = span(source, func)
            length = source.count_code_lines(
                location.line, location.end_line, docstring_lines(func)
            )
            if length > self.max_lines and not source.is_suppressed(func.lineno, self.rule):
                yield make_finding(
                    self.rule,
                    location,
                    f"function '{qualname}' has {length} lines of code (limit {self.max_lines})",
                    metric=length,
                    threshold=self.max_lines,
                    symbol=qualname,
                )
