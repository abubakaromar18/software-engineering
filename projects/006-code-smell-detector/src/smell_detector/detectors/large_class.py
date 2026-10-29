"""Large Class: classes with too many methods or too many lines of code.

Two signals are checked because they catch different problems: many tiny
methods suggest too many responsibilities, while few huge methods suggest
missing decomposition. When both exceed their limits, the finding is scored
by whichever is *relatively* worse, and the message reports both.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from smell_detector import scoring
from smell_detector.detectors.base import iter_classes, make_finding, span
from smell_detector.models import Finding
from smell_detector.source import SourceFile, docstring_lines


class LargeClassDetector:
    rule = "large-class"

    def __init__(self, max_methods: int, max_lines: int) -> None:
        self.max_methods = max_methods
        self.max_lines = max_lines

    def check(self, source: SourceFile) -> Iterator[Finding]:
        for cls, qualname in iter_classes(source.tree):
            if source.is_suppressed(cls.lineno, self.rule):
                continue
            location = span(source, cls)
            methods = sum(
                isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) for stmt in cls.body
            )
            lines = source.count_code_lines(location.line, location.end_line, docstring_lines(cls))
            # (metric, threshold, label) for each signal that is over its limit.
            exceeded = [
                (metric, limit, label)
                for metric, limit, label in (
                    (methods, self.max_methods, "methods"),
                    (lines, self.max_lines, "lines of code"),
                )
                if metric > limit
            ]
            if not exceeded:
                continue
            metric, limit, _ = max(exceeded, key=lambda item: scoring.score(item[0], item[1]))
            details = ", ".join(f"{m} {label} (limit {t})" for m, t, label in exceeded)
            yield make_finding(
                self.rule,
                location,
                f"class '{qualname}' is too large: {details}",
                metric=metric,
                threshold=limit,
                symbol=qualname,
            )
