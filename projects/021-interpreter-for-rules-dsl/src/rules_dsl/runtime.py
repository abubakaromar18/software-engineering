"""Evaluation context: the 'Context' participant of the Interpreter pattern.

The context owns everything nodes need at run time: input facts, the result
namespace rules write to, tags, and the function registry. Writes made by a
rule are staged and only committed when the whole rule succeeds, so a rule
that fails half-way leaves no partial effects behind.
"""

from __future__ import annotations

from collections import ChainMap
from collections.abc import Mapping
from dataclasses import dataclass, field

from .functions import FunctionRegistry
from .values import Value

RESULT_ROOT = "result"


@dataclass(frozen=True, slots=True)
class Change:
    name: str
    value: Value


@dataclass
class EvalContext:
    facts: Mapping[str, Value]
    functions: FunctionRegistry
    _committed: dict[str, Value] = field(default_factory=dict)
    _staged: dict[str, Value] = field(default_factory=dict)
    _tags: list[str] = field(default_factory=list)
    _staged_tags: list[str] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)
    stop_requested: bool = False

    # -- reads -------------------------------------------------------------

    def root(self, name: str) -> tuple[bool, Value]:
        """Resolve the first segment of a path. Returns ``(found, value)``."""
        if name == RESULT_ROOT:
            return True, dict(self.results)
        if name in self.facts:
            return True, self.facts[name]
        return False, None

    @property
    def results(self) -> Mapping[str, Value]:
        """Committed results overlaid with this rule's staged writes."""
        return ChainMap(self._staged, self._committed)

    @property
    def tags(self) -> list[str]:
        return [*self._tags, *(t for t in self._staged_tags if t not in self._tags)]

    # -- writes (staged) ---------------------------------------------------

    def assign(self, name: str, value: Value) -> None:
        self._staged[name] = value
        self.changes.append(Change(name, value))

    def add_tag(self, tag: str) -> None:
        if tag not in self._staged_tags:
            self._staged_tags.append(tag)

    # -- rule transactions -------------------------------------------------

    def begin(self) -> None:
        self._staged.clear()
        self._staged_tags.clear()
        self.changes = []
        self.stop_requested = False

    def commit(self) -> tuple[list[Change], bool]:
        """Apply staged writes. Returns this rule's changes and whether it requested stop."""
        changes, stop = self.changes, self.stop_requested
        self._committed.update(self._staged)
        self._tags = self.tags
        self.begin()
        return changes, stop

    def rollback(self) -> None:
        self.begin()
