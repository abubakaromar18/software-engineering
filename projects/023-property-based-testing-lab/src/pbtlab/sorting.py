"""Stable merge sort and friends.

Everything here is pure: inputs are never mutated and a fresh list is
returned. The comparison logic lives in one place (``_before``) so that
``reverse`` and ``key`` are handled identically by every function.
"""

from __future__ import annotations

import heapq
from collections.abc import Callable, Iterable, Sequence
from typing import Any, TypeVar

T = TypeVar("T")
Key = Callable[[T], Any]


def _identity(x: T) -> T:
    return x


def _before(a_key: Any, b_key: Any, reverse: bool) -> bool:
    """True if an element with ``a_key`` must come strictly before ``b_key``."""
    return b_key < a_key if reverse else a_key < b_key


def merge(
    left: Sequence[T], right: Sequence[T], *, key: Key | None = None, reverse: bool = False
) -> list[T]:
    """Merge two already-sorted sequences into one sorted list.

    Stability: when keys are equal the element from ``left`` wins, so
    ``merge`` preserves the relative order of equal elements as long as
    ``left`` came first in the original input.
    """
    key = key or _identity
    out: list[T] = []
    i = j = 0
    while i < len(left) and j < len(right):
        # Take from the right only if it is *strictly* first; ties go left.
        if _before(key(right[j]), key(left[i]), reverse):
            out.append(right[j])
            j += 1
        else:
            out.append(left[i])
            i += 1
    out.extend(left[i:])
    out.extend(right[j:])
    return out


def merge_sort(items: Iterable[T], *, key: Key | None = None, reverse: bool = False) -> list[T]:
    """Return a new list sorted by ``key``, stable, mirroring ``sorted()``.

    Like ``sorted(reverse=True)``, reversing keeps equal elements in their
    original order rather than reversing them.
    """
    data = list(items)
    if len(data) <= 1:
        return data
    mid = len(data) // 2
    return merge(
        merge_sort(data[:mid], key=key, reverse=reverse),
        merge_sort(data[mid:], key=key, reverse=reverse),
        key=key,
        reverse=reverse,
    )


def is_sorted(items: Sequence[T], *, key: Key | None = None, reverse: bool = False) -> bool:
    """True if no adjacent pair is out of order."""
    key = key or _identity
    return not any(
        _before(key(items[i + 1]), key(items[i]), reverse) for i in range(len(items) - 1)
    )


def top_k(items: Iterable[T], k: int, *, key: Key | None = None) -> list[T]:
    """The ``k`` smallest items in sorted order, stable among equal keys.

    Runs in O(n log k). Raises ``ValueError`` for negative ``k``.
    """
    if k < 0:
        raise ValueError(f"k must be non-negative, got {k}")
    key = key or _identity
    # Pair each item with its position so ties are broken by input order
    # and items themselves are never compared.
    indexed = heapq.nsmallest(k, enumerate(items), key=lambda pair: (key(pair[1]), pair[0]))
    return [item for _, item in indexed]
