"""Count-Min sketch: frequency estimation in sub-linear space.

The sketch is a ``depth x width`` grid of counters. Each row has its own hash
function; adding ``x`` increments one counter per row, and the estimate for
``x`` is the *minimum* of its ``depth`` counters. Collisions only ever add to
a counter, so the estimate never under-counts. Cormode & Muthukrishnan (2005)
show that with

    width = ceil(e / epsilon)      depth = ceil(ln(1 / delta))

the over-count is at most ``epsilon * N`` (``N`` = total count added) with
probability at least ``1 - delta``.

*Conservative update* (Estan & Varghese, 2002) raises each counter only as far
as needed to keep the new minimum correct. It keeps the same guarantee and
is often several times more accurate on skewed streams, at the cost of
making the sketch insert-only (no decrements).
"""

from __future__ import annotations

import math
from array import array
from collections.abc import Iterable

from sketches.hashing import Hashable, indexes


class CountMinSketch:
    """A Count-Min sketch over ``str``, ``bytes`` and ``int`` items."""

    def __init__(
        self,
        width: int,
        depth: int,
        *,
        seed: int = 0,
        conservative: bool = False,
    ) -> None:
        if width < 1:
            raise ValueError("width must be at least 1")
        if depth < 1:
            raise ValueError("depth must be at least 1")
        self._width = width
        self._depth = depth
        self._seed = seed
        self._conservative = conservative
        # Unsigned 64-bit counters: compact, and counts are never negative.
        self._rows = [array("Q", bytes(8 * width)) for _ in range(depth)]
        self._total = 0

    @classmethod
    def from_error(
        cls,
        epsilon: float,
        delta: float,
        *,
        seed: int = 0,
        conservative: bool = False,
    ) -> CountMinSketch:
        """Size a sketch so ``estimate <= true + epsilon*N`` w.p. ``>= 1 - delta``."""
        if not 0.0 < epsilon < 1.0:
            raise ValueError("epsilon must be strictly between 0 and 1")
        if not 0.0 < delta < 1.0:
            raise ValueError("delta must be strictly between 0 and 1")
        width = math.ceil(math.e / epsilon)
        depth = math.ceil(math.log(1.0 / delta))
        return cls(width, depth, seed=seed, conservative=conservative)

    # -- core operations --------------------------------------------------

    def _cells(self, item: Hashable) -> list[int]:
        # One index per row; row r uses the r-th member of the hash family.
        return list(indexes(item, self._depth, self._width, self._seed))

    def add(self, item: Hashable, count: int = 1) -> int:
        """Add ``count`` occurrences of ``item`` and return its new estimate."""
        if count < 0:
            raise ValueError("count must be non-negative; Count-Min is insert-only here")
        cells = self._cells(item)
        self._total += count
        if self._conservative:
            target = min(row[col] for row, col in zip(self._rows, cells)) + count
            for row, col in zip(self._rows, cells):
                if row[col] < target:
                    row[col] = target
            return target
        for row, col in zip(self._rows, cells):
            row[col] += count
        return min(row[col] for row, col in zip(self._rows, cells))

    def update(self, items: Iterable[Hashable]) -> None:
        for item in items:
            self.add(item)

    def estimate(self, item: Hashable) -> int:
        """Upper-bound estimate of how many times ``item`` was added."""
        return min(row[col] for row, col in zip(self._rows, self._cells(item)))

    def __getitem__(self, item: Hashable) -> int:
        return self.estimate(item)

    # -- introspection ----------------------------------------------------

    @property
    def width(self) -> int:
        return self._width

    @property
    def depth(self) -> int:
        return self._depth

    @property
    def total(self) -> int:
        """``N``: the sum of all counts added."""
        return self._total

    @property
    def conservative(self) -> bool:
        return self._conservative

    @property
    def epsilon(self) -> float:
        """Relative error achieved by this width: ``e / width``."""
        return math.e / self._width

    @property
    def delta(self) -> float:
        """Failure probability achieved by this depth: ``e^-depth``."""
        return math.exp(-self._depth)

    def error_bound(self) -> float:
        """Absolute over-count bound ``epsilon * N`` that holds w.p. ``1 - delta``."""
        return self.epsilon * self._total

    @property
    def memory_bytes(self) -> int:
        return self._width * self._depth * 8

    # -- combination ------------------------------------------------------

    def merge(self, other: CountMinSketch) -> None:
        """Add ``other``'s counters into this sketch (in place).

        Valid because every cell is a sum over the items hashed to it; for
        conservative sketches the cell-wise sum is still an upper bound.
        """
        if not isinstance(other, CountMinSketch):
            raise TypeError("operand must be a CountMinSketch")
        if (self._width, self._depth, self._seed) != (other._width, other._depth, other._seed):
            raise ValueError("sketches must share width, depth and seed")
        for mine, theirs in zip(self._rows, other._rows):
            for col, value in enumerate(theirs):
                mine[col] += value
        self._total += other._total

    def __repr__(self) -> str:
        mode = ", conservative" if self._conservative else ""
        return f"CountMinSketch(width={self._width}, depth={self._depth}, total={self._total}{mode})"


class TopK:
    """Track the ``k`` most frequent items of a stream using a Count-Min sketch.

    The sketch provides frequency estimates for any item; a small candidate
    table remembers *which* items are worth reporting. Memory is
    ``O(sketch + k)`` regardless of how many distinct items the stream has.
    Because estimates over-count, an infrequent item that collides with heavy
    ones can briefly enter the table; a larger sketch makes that rarer.
    """

    def __init__(self, k: int, sketch: CountMinSketch) -> None:
        if k < 1:
            raise ValueError("k must be at least 1")
        self._k = k
        self._sketch = sketch
        self._candidates: dict[Hashable, int] = {}

    @property
    def sketch(self) -> CountMinSketch:
        return self._sketch

    def add(self, item: Hashable, count: int = 1) -> None:
        estimate = self._sketch.add(item, count)
        if item in self._candidates or len(self._candidates) < self._k:
            self._candidates[item] = estimate
            return
        # Evict the weakest candidate if the newcomer beats it. O(k) per
        # eviction is fine for the small k this is designed for.
        weakest = min(self._candidates, key=self._candidates.__getitem__)
        if estimate > self._candidates[weakest]:
            del self._candidates[weakest]
            self._candidates[item] = estimate

    def update(self, items: Iterable[Hashable]) -> None:
        for item in items:
            self.add(item)

    def items(self) -> list[tuple[Hashable, int]]:
        """Candidates sorted by estimated frequency, highest first."""
        refreshed = [(item, self._sketch.estimate(item)) for item in self._candidates]
        return sorted(refreshed, key=lambda pair: (-pair[1], str(pair[0])))
