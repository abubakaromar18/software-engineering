"""Generic AST traversal for operations other than evaluation.

The Interpreter pattern makes adding a node type easy but adding an operation
means touching every node. A visitor flips that trade-off for the operations
that are not evaluation (static checks, formatting), so both are cheap here.
Dispatch is by method name (``visit_Binary``), like :class:`ast.NodeVisitor`.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import fields
from typing import Any

from .nodes import Node


def children(node: Node) -> Iterator[Node]:
    """Yield the direct child nodes of ``node`` in field order."""
    for spec in fields(node):
        value = getattr(node, spec.name)
        if isinstance(value, Node):
            yield value
        elif isinstance(value, tuple):
            yield from (item for item in value if isinstance(item, Node))


def walk(node: Node) -> Iterator[Node]:
    """Pre-order traversal of ``node`` and all its descendants."""
    yield node
    for child in children(node):
        yield from walk(child)


class NodeVisitor:
    def visit(self, node: Node) -> Any:
        method = getattr(self, f"visit_{type(node).__name__}", self.generic_visit)
        return method(node)

    def generic_visit(self, node: Node) -> Any:
        for child in children(node):
            self.visit(child)
        return None
