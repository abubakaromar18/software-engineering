"""Duplicate Blocks: runs of consecutive statements that appear more than once.

Approach (a token-free variant of classic clone detection):

1. **Fingerprint** every statement from its AST with identifiers and literal
   values erased, so ``total = price * qty`` and ``s = p * n`` match. This
   finds copy-paste-then-rename clones ("Type-2" clones), not just exact text.
2. **Index** every window of ``min_statements`` consecutive fingerprints in
   every statement list (function bodies, loop bodies, branches, ...) across
   all files.
3. **Extend** each window that occurs at least twice for as long as all of its
   copies keep matching, giving the maximal clone.
4. **Prune** clones whose every copy lies inside a larger reported clone.

Trade-offs: erasing all names means a block that only *shapes* like another
(same structure, unrelated variables) can match. Requiring several statements
and a minimum number of lines keeps such coincidences rare. Import statements
never take part in a clone, since repeated import headers are not duplication
worth refactoring.
"""

from __future__ import annotations

import ast
import hashlib
from collections import defaultdict
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from smell_detector.detectors.base import make_finding
from smell_detector.models import Finding, Location
from smell_detector.source import SourceFile

# Fields whose string values are names chosen by the author, not structure.
_ERASED_STRINGS = {(ast.Name, "id"), (ast.arg, "arg")}
_IGNORED_FIELDS = {"type_comment"}


def fingerprint(node: ast.AST) -> str:
    """A stable digest of ``node``'s structure with names and literals erased."""
    return hashlib.blake2b(_shape(node).encode(), digest_size=8).hexdigest()


def _shape(node: ast.AST) -> str:
    if isinstance(node, ast.Constant):
        return f"Constant<{type(node.value).__name__}>"
    parts = [type(node).__name__]
    for name, value in ast.iter_fields(node):
        if name in _IGNORED_FIELDS:
            continue
        if isinstance(value, ast.AST):
            parts.append(f"{name}=({_shape(value)})")
        elif isinstance(value, list):
            items = ",".join(_shape(v) if isinstance(v, ast.AST) else repr(v) for v in value)
            parts.append(f"{name}=[{items}]")
        elif isinstance(value, str) and (type(node), name) in _ERASED_STRINGS:
            parts.append(f"{name}=_")
        else:
            parts.append(f"{name}={value!r}")
    return " ".join(parts)


@dataclass(frozen=True)
class _Block:
    """One statement list (a ``body``, ``orelse``, ...) and its fingerprints."""

    source: SourceFile
    statements: Sequence[ast.stmt]
    prints: tuple[str | None, ...]  # ``None`` marks a statement that can't join a clone

    def location(self, start: int, length: int) -> Location:
        first, last = self.statements[start], self.statements[start + length - 1]
        return Location(self.source.path, first.lineno, last.end_lineno or last.lineno)


@dataclass(frozen=True)
class _Occurrence:
    block: int
    start: int


def _statement_lists(tree: ast.AST) -> Iterator[list[ast.stmt]]:
    for node in ast.walk(tree):
        for _, value in ast.iter_fields(node):
            if isinstance(value, list) and value and isinstance(value[0], ast.stmt):
                yield value


def _print_of(stmt: ast.stmt) -> str | None:
    if isinstance(stmt, (ast.Import, ast.ImportFrom)):
        return None
    return fingerprint(stmt)


class DuplicateBlockDetector:
    rule = "duplicate-block"

    def __init__(self, min_statements: int, min_lines: int) -> None:
        self.min_statements = min_statements
        self.min_lines = min_lines

    def check_project(self, sources: Sequence[SourceFile]) -> Iterator[Finding]:
        blocks = [
            _Block(source, stmts, tuple(_print_of(s) for s in stmts))
            for source in sources
            for stmts in _statement_lists(source.tree)
            if len(stmts) >= self.min_statements
        ]
        clones = [self._extend(blocks, occ) for occ in self._repeated_windows(blocks)]
        yield from self._report(blocks, clones)

    def _repeated_windows(self, blocks: list[_Block]) -> Iterator[list[_Occurrence]]:
        """Groups of non-overlapping positions that share a window of fingerprints."""
        n = self.min_statements
        index: dict[tuple[str, ...], list[_Occurrence]] = defaultdict(list)
        for b, block in enumerate(blocks):
            for start in range(len(block.prints) - n + 1):
                window = block.prints[start : start + n]
                if None not in window:
                    index[window].append(_Occurrence(b, start))  # type: ignore[arg-type]
        for occurrences in index.values():
            kept = _without_self_overlap(occurrences, n)
            if len(kept) >= 2:
                yield kept

    def _extend(
        self, blocks: list[_Block], occurrences: list[_Occurrence]
    ) -> tuple[list[_Occurrence], int]:
        """Grow the clone while every copy's next statement still matches."""
        length = self.min_statements
        while True:
            nxt = [
                blocks[o.block].prints[o.start + length]
                if o.start + length < len(blocks[o.block].prints)
                else None
                for o in occurrences
            ]
            if nxt[0] is None or any(p != nxt[0] for p in nxt):
                break
            if len(_without_self_overlap(occurrences, length + 1)) != len(occurrences):
                break
            length += 1
        return occurrences, length

    def _suppressed(self, block: _Block, start: int) -> bool:
        return block.source.is_suppressed(block.statements[start].lineno, self.rule)

    def _groups(
        self, blocks: list[_Block], clones: list[tuple[list[_Occurrence], int]]
    ) -> list[tuple[int, list[Location]]]:
        """Turn clones into ``(code lines, locations)``, dropping suppressed or too-small ones."""
        groups: list[tuple[int, list[Location]]] = []
        for occurrences, length in clones:
            copies = sorted(
                (
                    (blocks[o.block].location(o.start, length), blocks[o.block].source)
                    for o in occurrences
                    if not self._suppressed(blocks[o.block], o.start)
                ),
                key=lambda copy: copy[0],
            )
            if len(copies) < 2:
                continue
            lines = min(src.count_code_lines(loc.line, loc.end_line) for loc, src in copies)
            if lines >= self.min_lines:
                groups.append((lines, [loc for loc, _ in copies]))
        return groups

    def _report(
        self, blocks: list[_Block], clones: list[tuple[list[_Occurrence], int]]
    ) -> Iterator[Finding]:
        groups = self._groups(blocks, clones)
        # Largest clones first, so the sub-windows they contain are pruned.
        groups.sort(key=lambda g: (-g[0], g[1]))
        reported: list[Location] = []
        for lines, locations in groups:
            if all(any(big.contains(loc) for big in reported) for loc in locations):
                continue
            reported.extend(locations)
            first, *others = locations
            redundant = lines * (len(locations) - 1)
            yield make_finding(
                self.rule,
                first,
                f"{lines}-line block appears {len(locations)} times "
                f"({redundant} redundant lines); also at {', '.join(map(str, others))}",
                metric=redundant,
                threshold=self.min_lines,
                related=tuple(others),
            )


def _without_self_overlap(occurrences: list[_Occurrence], length: int) -> list[_Occurrence]:
    """Drop copies that overlap an earlier copy in the same statement list.

    Without this, six identical statements in a row would "duplicate" themselves.
    """
    kept: list[_Occurrence] = []
    last_end: dict[int, int] = {}
    for occ in sorted(occurrences, key=lambda o: (o.block, o.start)):
        if occ.start >= last_end.get(occ.block, -1):
            kept.append(occ)
            last_end[occ.block] = occ.start + length
    return kept
