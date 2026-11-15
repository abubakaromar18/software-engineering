"""Buggy implementations kept on purpose, like specimens in a jar.

Each function is a plausible first draft of something in this library and
contains one realistic bug. None of them fail on the "obvious" hand-written
example next to it, which is the point: :mod:`pbtlab.hunts` lets Hypothesis
find and shrink an input that exposes each one.

Do not import these from production code.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from datetime import date
from typing import Any

from pbtlab.dateranges import DateRange

# ---------------------------------------------------------------- sorting


def merge_sort_unstable(items: Iterable[Any], *, key: Callable[[Any], Any] | None = None) -> list:
    """Bug: ties go to the *right* half (``<=`` instead of ``<``), breaking stability.

    Hand test that passes: ``merge_sort_unstable([3, 1, 2]) == [1, 2, 3]``.
    """
    key = key or (lambda x: x)
    data = list(items)
    if len(data) <= 1:
        return data
    mid = len(data) // 2
    left = merge_sort_unstable(data[:mid], key=key)
    right = merge_sort_unstable(data[mid:], key=key)
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if key(right[j]) <= key(left[i]):
            out.append(right[j])
            j += 1
        else:
            out.append(left[i])
            i += 1
    return out + left[i:] + right[j:]


def merge_sort_drops_tail(items: Iterable[Any]) -> list:
    """Bug: after the merge loop only the left remainder is copied.

    Hand test that passes: ``merge_sort_drops_tail([2, 1]) == [1, 2]``.
    """
    data = list(items)
    if len(data) <= 1:
        return data
    mid = len(data) // 2
    left, right = merge_sort_drops_tail(data[:mid]), merge_sort_drops_tail(data[mid:])
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if right[j] < left[i]:
            out.append(right[j])
            j += 1
        else:
            out.append(left[i])
            i += 1
    return out + left[i:]


# --------------------------------------------------------------- encoding


def rle_encode_naive(text: str) -> str:
    """Bug: digits in the data are not escaped, so counts and data collide.

    Hand test that passes: ``rle_encode_naive("aaab") == "3a1b"``.
    """
    out, i = [], 0
    while i < len(text):
        j = i
        while j < len(text) and text[j] == text[i]:
            j += 1
        out.append(f"{j - i}{text[i]}")
        i = j
    return "".join(out)


def rle_decode_naive(encoded: str) -> str:
    """Decoder matching :func:`rle_encode_naive` (greedy digits, then one char)."""
    out, i = [], 0
    while i < len(encoded):
        start = i
        while i < len(encoded) and encoded[i] in "0123456789":
            i += 1
        if i == start or i >= len(encoded):
            raise ValueError(f"malformed run at position {start}")
        out.append(encoded[i] * int(encoded[start:i]))
        i += 1
    return "".join(out)


def rle_decode_single_digit(encoded: str) -> str:
    """Bug: assumes counts are one digit, so runs of 10+ decode wrongly.

    Pairs with the correct :func:`pbtlab.encoding.rle_encode`.
    Hand test that passes: ``rle_decode_single_digit("3a1b") == "aaab"``.
    """
    out, i = [], 0
    while i < len(encoded):
        count = int(encoded[i])
        i += 1
        if encoded[i] == "\\":
            i += 1
        out.append(encoded[i] * count)
        i += 1
    return "".join(out)


def zigzag_fixed64(value: int) -> int:
    """Bug: the classic C idiom ``(n << 1) ^ (n >> 63)`` assumes 64-bit ints.

    Python ints are unbounded, so values outside int64 no longer round-trip.
    Hand test that passes: ``zigzag_fixed64(-1) == 1``.
    """
    return (value << 1) ^ (value >> 63)


# ------------------------------------------------------------ date ranges


def overlaps_inclusive(a: DateRange, b: DateRange) -> bool:
    """Bug: compares with ``<=`` as if ``end`` were inclusive.

    Adjacent ranges ``[a, b)`` and ``[b, c)`` are reported as overlapping.
    Hand test that passes: Jan 1-10 overlaps Jan 5-15.
    """
    return a.start <= b.end and b.start <= a.end


def merge_without_sorting(ranges: Iterable[DateRange]) -> list[DateRange]:
    """Bug: coalesces neighbours in input order, forgetting to sort first.

    Hand test that passes: already-sorted input.
    """
    merged: list[DateRange] = []
    for current in (r for r in ranges if not r.is_empty):
        if merged and current.start <= merged[-1].end:
            last = merged[-1]
            merged[-1] = DateRange(last.start, max(last.end, current.end))
        else:
            merged.append(current)
    return merged


def split_by_month_naive(span: DateRange) -> Sequence[DateRange]:
    """Bug: ``date(y, m + 1, 1)`` raises in December.

    Hand test that passes: any range from February to November.
    """
    pieces, cursor = [], span.start
    while cursor < span.end:
        boundary = min(date(cursor.year, cursor.month + 1, 1), span.end)
        pieces.append(DateRange(cursor, boundary))
        cursor = boundary
    return pieces
