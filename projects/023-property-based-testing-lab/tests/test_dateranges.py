"""Properties of DateRange, merge and split_by_month.

The model used throughout is "a range is a set of days". Every operation
is checked against what it should do to that set, which is slow but
obviously correct, so the fast interval arithmetic is held to it.
"""

from datetime import date, timedelta

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from pbtlab import strategies as pst
from pbtlab.dateranges import DateRange, first_of_next_month, merge, split_by_month


def days_of(ranges):
    return {d for r in ranges for d in r}


ranges = pst.date_ranges()
pairs = st.tuples(ranges, ranges) | pst.adjacent_pairs()


@given(ranges)
def test_length_matches_iteration(r):
    assert r.days == len(list(r))


@given(ranges, pst.dates)
def test_contains_matches_iteration(r, day):
    assert (day in r) == (day in set(r))


@given(pairs)
@example(
    (DateRange(date(2100, 1, 1), date(2100, 1, 2)), DateRange(date(2100, 1, 2), date(2100, 1, 3)))
)  # adjacent ranges share no day
@example(
    (DateRange(date(2095, 1, 1), date(2095, 1, 3)), DateRange(date(2095, 1, 2), date(2095, 1, 2)))
)  # regression: an empty range inside another one was reported as overlapping
def test_overlaps_iff_a_shared_day(pair):
    a, b = pair
    assert a.overlaps(b) == bool(set(a) & set(b))


@given(pairs)
def test_overlaps_is_symmetric(pair):
    a, b = pair
    assert a.overlaps(b) == b.overlaps(a)


@given(pairs)
def test_intersection_is_set_intersection(pair):
    a, b = pair
    shared = a.intersection(b)
    assert (set(shared) if shared else set()) == set(a) & set(b)


@given(pst.adjacent_pairs())
def test_adjacent_ranges_never_overlap(pair):
    a, b = pair
    assert not a.overlaps(b)


@given(pst.dates, st.integers(min_value=0, max_value=400))
def test_inclusive_constructor(first, extra):
    last = first + timedelta(days=extra)
    r = DateRange.inclusive(first, last)
    assert first in r and last in r
    assert r.days == extra + 1


def test_rejects_end_before_start():
    with pytest.raises(ValueError, match="before start"):
        DateRange(date(2100, 1, 2), date(2100, 1, 1))


# ------------------------------------------------------------- merge


@given(st.lists(ranges, max_size=8))
def test_merge_preserves_days(rs):
    assert days_of(merge(rs)) == days_of(rs)


@given(st.lists(ranges, max_size=8))
@example(
    [DateRange(date(2095, 1, 2), date(2095, 1, 3)), DateRange(date(2095, 1, 1), date(2095, 1, 2))]
)
def test_merge_is_canonical(rs):
    out = merge(rs)
    assert all(not r.is_empty for r in out)
    # strictly increasing with a gap: sorted, disjoint and not touching
    assert all(x.end < y.start for x, y in zip(out, out[1:], strict=False))


@given(st.lists(ranges, max_size=8))
def test_merge_is_idempotent(rs):
    assert merge(merge(rs)) == merge(rs)


@given(st.lists(ranges, max_size=8), st.randoms(use_true_random=False))
def test_merge_ignores_input_order(rs, rnd):
    shuffled = list(rs)
    rnd.shuffle(shuffled)
    assert merge(shuffled) == merge(rs)


# ----------------------------------------------------- split_by_month


@given(ranges)
@example(DateRange(date(2095, 12, 15), date(2096, 1, 15)))  # regression: December crash
def test_split_reassembles(r):
    pieces = split_by_month(r)
    assert [d for p in pieces for d in p] == list(r)


@given(ranges)
def test_split_pieces_stay_in_one_month(r):
    for piece in split_by_month(r):
        assert not piece.is_empty
        last = piece.end - timedelta(days=1)
        assert (piece.start.year, piece.start.month) == (last.year, last.month)


@given(ranges)
def test_split_count_is_months_touched(r):
    months = {(d.year, d.month) for d in r}
    assert len(split_by_month(r)) == len(months)


@given(pst.dates)
def test_first_of_next_month(day):
    nxt = first_of_next_month(day)
    assert nxt.day == 1
    assert nxt > day
    assert (nxt - timedelta(days=1)).month == day.month


def test_split_handles_leap_february_2096_and_not_2100():
    assert [p.days for p in split_by_month(DateRange(date(2096, 2, 1), date(2096, 3, 1)))] == [29]
    assert [p.days for p in split_by_month(DateRange(date(2100, 2, 1), date(2100, 3, 1)))] == [28]
