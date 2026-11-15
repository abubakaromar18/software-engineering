"""Half-open date ranges ``[start, end)`` and a normalised set of them.

Half-open intervals are the deliberate core decision: adjacent ranges
``[a, b)`` and ``[b, c)`` share no day, lengths are ``end - start`` with no
``+ 1``, and splitting at any date ``m`` gives ``[a, m)`` and ``[m, c)``
with nothing lost or duplicated.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, timedelta

_ONE_DAY = timedelta(days=1)


@dataclass(frozen=True, order=True, slots=True, repr=False)
class DateRange:
    """Every date ``d`` with ``start <= d < end``. ``start == end`` is empty."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"range end {self.end} is before start {self.start}")

    def __repr__(self) -> str:
        return f"DateRange({self.start.isoformat()}, {self.end.isoformat()})"

    @classmethod
    def inclusive(cls, first: date, last: date) -> DateRange:
        """Build from an inclusive last day, as humans usually write ranges."""
        return cls(first, last + _ONE_DAY)

    @property
    def days(self) -> int:
        return (self.end - self.start).days

    @property
    def is_empty(self) -> bool:
        return self.start == self.end

    def __contains__(self, day: object) -> bool:
        return isinstance(day, date) and self.start <= day < self.end

    def __iter__(self) -> Iterator[date]:
        day = self.start
        while day < self.end:
            yield day
            day += _ONE_DAY

    def overlaps(self, other: DateRange) -> bool:
        """True if at least one day is in both ranges.

        Empty ranges overlap nothing, even when they sit inside another range;
        Hypothesis found ``[Jan 1, Jan 3)`` vs ``[Jan 2, Jan 2)`` during development.
        """
        if self.is_empty or other.is_empty:
            return False
        return self.start < other.end and other.start < self.end

    def intersection(self, other: DateRange) -> DateRange | None:
        """The shared days, or ``None`` if there are none."""
        if not self.overlaps(other):
            return None
        return DateRange(max(self.start, other.start), min(self.end, other.end))


def merge(ranges: Iterable[DateRange]) -> list[DateRange]:
    """Union of ``ranges`` as a sorted list of disjoint, non-touching, non-empty ranges."""
    merged: list[DateRange] = []
    for current in sorted(r for r in ranges if not r.is_empty):
        # Touching (end == start) ranges are coalesced as well as overlapping ones.
        if merged and current.start <= merged[-1].end:
            last = merged[-1]
            merged[-1] = DateRange(last.start, max(last.end, current.end))
        else:
            merged.append(current)
    return merged


def first_of_next_month(day: date) -> date:
    """The 1st of the month after ``day``'s month (rolls over the year)."""
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def split_by_month(span: DateRange) -> list[DateRange]:
    """Cut ``span`` at every month boundary; the pieces concatenate back to ``span``."""
    pieces: list[DateRange] = []
    cursor = span.start
    while cursor < span.end:
        boundary = min(first_of_next_month(cursor), span.end)
        pieces.append(DateRange(cursor, boundary))
        cursor = boundary
    return pieces


class RangeSet:
    """A mutable set of days stored as merged ranges.

    Invariant (checked by the stateful tests): ``ranges`` is always the
    canonical output of :func:`merge`, i.e. sorted, disjoint, non-touching
    and free of empty ranges.
    """

    def __init__(self, ranges: Iterable[DateRange] = ()) -> None:
        self._ranges: list[DateRange] = merge(ranges)

    @property
    def ranges(self) -> tuple[DateRange, ...]:
        return tuple(self._ranges)

    @property
    def total_days(self) -> int:
        return sum(r.days for r in self._ranges)

    def __contains__(self, day: object) -> bool:
        return any(day in r for r in self._ranges)

    def __len__(self) -> int:
        return len(self._ranges)

    def add(self, span: DateRange) -> None:
        self._ranges = merge([*self._ranges, span])

    def remove(self, span: DateRange) -> None:
        """Remove every day of ``span``, splitting stored ranges as needed."""
        if span.is_empty:
            return
        kept: list[DateRange] = []
        for r in self._ranges:
            if not r.overlaps(span):
                kept.append(r)
                continue
            if r.start < span.start:
                kept.append(DateRange(r.start, span.start))
            if span.end < r.end:
                kept.append(DateRange(span.end, r.end))
        self._ranges = kept

    def __repr__(self) -> str:
        return f"RangeSet({list(self._ranges)!r})"
