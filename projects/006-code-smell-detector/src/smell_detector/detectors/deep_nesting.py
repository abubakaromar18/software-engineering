"""Deep Nesting: control-flow blocks stacked too deeply inside one function.

Depth counts block statements (``if``, loops, ``with``, ``try``, ``match``)
between the function body and the innermost statement. Two details matter:

* ``elif`` is stored by ``ast`` as an ``If`` nested in ``orelse``. It reads as
  a flat chain, so it is measured at the *same* depth as its ``if``.
* A nested ``def``/``class``/``lambda`` starts a fresh scope. Its body is
  measured when that function is visited, not charged to the outer one.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from smell_detector.detectors.base import iter_functions, make_finding, span
from smell_detector.models import Finding
from smell_detector.source import SourceFile

_BLOCKS = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.TryStar,
    ast.Match,
)
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


def max_depth(func: ast.AST) -> tuple[int, int]:
    """Return ``(deepest nesting, line where it occurs)`` for a function body."""
    best = (0, getattr(func, "lineno", 0))

    def visit(node: ast.AST, depth: int) -> None:
        nonlocal best
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _SCOPES):
                continue
            if _is_elif(node, child):
                visit(child, depth)  # same level as the parent ``if``
            elif isinstance(child, _BLOCKS):
                if depth + 1 > best[0]:
                    best = (depth + 1, child.lineno)
                visit(child, depth + 1)
            else:
                visit(child, depth)

    visit(func, 0)
    return best


def _is_elif(parent: ast.AST, child: ast.AST) -> bool:
    return (
        isinstance(parent, ast.If)
        and isinstance(child, ast.If)
        and len(parent.orelse) == 1
        and parent.orelse[0] is child
    )


class DeepNestingDetector:
    rule = "deep-nesting"

    def __init__(self, max_depth: int) -> None:
        self.max_depth = max_depth

    def check(self, source: SourceFile) -> Iterator[Finding]:
        for func, qualname in iter_functions(source.tree):
            depth, deepest_line = max_depth(func)
            if depth > self.max_depth and not source.is_suppressed(func.lineno, self.rule):
                yield make_finding(
                    self.rule,
                    span(source, func),
                    f"function '{qualname}' nests blocks {depth} deep at line {deepest_line} "
                    f"(limit {self.max_depth})",
                    metric=depth,
                    threshold=self.max_depth,
                    symbol=qualname,
                )
