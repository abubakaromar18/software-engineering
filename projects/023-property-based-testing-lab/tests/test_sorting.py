"""Properties of merge_sort, merge and top_k.

The oracle here is Python's own ``sorted``, which is known to be stable.
Where an oracle exists, comparing against it is the strongest property;
the "structural" properties below are kept because they still say *what*
went wrong when the oracle comparison fails.
"""

from collections import Counter

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from pbtlab import strategies as pst
from pbtlab.sorting import is_sorted, merge, merge_sort, top_k

ints = st.lists(st.integers())
first = lambda record: record[0]  # noqa: E731 - tiny key function


@given(ints)
def test_matches_builtin_sorted(xs):
    assert merge_sort(xs) == sorted(xs)


@given(ints)
def test_output_is_ordered(xs):
    assert is_sorted(merge_sort(xs))


@given(ints)
@example([0, 0])  # regression: once lost the tail of the right half
def test_output_is_a_permutation(xs):
    assert Counter(merge_sort(xs)) == Counter(xs)


@given(ints)
def test_idempotent(xs):
    once = merge_sort(xs)
    assert merge_sort(once) == once


@given(ints)
def test_does_not_mutate_input(xs):
    snapshot = list(xs)
    merge_sort(xs)
    assert xs == snapshot


@given(pst.keyed_records(), st.booleans())
@example([(0, 0), (0, 1)], False)  # regression: ties once went to the right half
def test_stable_with_key_and_reverse(records, reverse):
    assert merge_sort(records, key=first, reverse=reverse) == sorted(
        records, key=first, reverse=reverse
    )


@given(st.lists(st.text()))
def test_works_for_any_total_order(words):
    assert merge_sort(words, key=str.casefold) == sorted(words, key=str.casefold)


@given(ints, ints)
def test_merge_of_sorted_halves_is_sorted_union(a, b):
    a, b = sorted(a), sorted(b)
    assert merge(a, b) == sorted(a + b)


@given(pst.keyed_records(), st.integers(min_value=0, max_value=60))
def test_top_k_is_prefix_of_stable_sort(records, k):
    assert top_k(records, k, key=first) == sorted(records, key=first)[:k]


@given(ints, st.integers(min_value=0, max_value=60))
def test_top_k_length(xs, k):
    assert len(top_k(xs, k)) == min(k, len(xs))


def test_top_k_rejects_negative_k():
    with pytest.raises(ValueError, match="non-negative"):
        top_k([1, 2, 3], -1)


def test_is_sorted_examples():
    assert is_sorted([])
    assert is_sorted([1, 1, 2])
    assert not is_sorted([2, 1])
    assert is_sorted([3, 2, 2], reverse=True)
