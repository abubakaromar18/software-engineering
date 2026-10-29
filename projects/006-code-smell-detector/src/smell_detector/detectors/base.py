"""Detector interfaces and the shared finding factory.

Two kinds of detector exist because some smells are local to one file and
others (duplication) only show up when files are compared:

* ``FileDetector.check(source)`` sees one file at a time.
* ``ProjectDetector.check_project(sources)`` sees every file at once.

The analyzer depends only on these protocols, so adding a rule never means
touching the analyzer (Open/Closed).
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Iterator, Sequence
from typing import Protocol, runtime_checkable

from smell_detector import scoring
from smell_detector.models import Finding, Location
from smell_detector.source import SourceFile

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


@runtime_checkable
class FileDetector(Protocol):
    rule: str

    def check(self, source: SourceFile) -> Iterable[Finding]: ...


@runtime_checkable
class ProjectDetector(Protocol):
    rule: str

    def check_project(self, sources: Sequence[SourceFile]) -> Iterable[Finding]: ...


def make_finding(
    rule: str,
    location: Location,
    message: str,
    metric: int,
    threshold: int,
    symbol: str | None = None,
    related: tuple[Location, ...] = (),
) -> Finding:
    """Build a finding with score and severity derived consistently for every rule."""
    points = scoring.score(metric, threshold)
    return Finding(
        rule=rule,
        location=location,
        message=message,
        metric=metric,
        threshold=threshold,
        score=points,
        severity=scoring.severity_for(points),
        symbol=symbol,
        related=related,
    )


def iter_functions(tree: ast.AST) -> Iterator[tuple[FunctionNode, str]]:
    """Yield every function and method with a dotted qualified name (``Cls.method``)."""

    def walk(node: ast.AST, prefix: str) -> Iterator[tuple[FunctionNode, str]]:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{prefix}{child.name}"
                yield child, name
                yield from walk(child, f"{name}.<locals>.")
            elif isinstance(child, ast.ClassDef):
                yield from walk(child, f"{prefix}{child.name}.")
            else:
                yield from walk(child, prefix)

    yield from walk(tree, "")


def iter_classes(tree: ast.AST) -> Iterator[tuple[ast.ClassDef, str]]:
    """Yield every class, including nested ones, with a qualified name."""

    def walk(node: ast.AST, prefix: str) -> Iterator[tuple[ast.ClassDef, str]]:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                name = f"{prefix}{child.name}"
                yield child, name
                yield from walk(child, f"{name}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield from walk(child, f"{prefix}{child.name}.<locals>.")
            else:
                yield from walk(child, prefix)

    yield from walk(tree, "")


def span(source: SourceFile, node: ast.AST) -> Location:
    start = node.lineno  # type: ignore[attr-defined]
    return Location(source.path, start, node.end_lineno or start)  # type: ignore[attr-defined]
