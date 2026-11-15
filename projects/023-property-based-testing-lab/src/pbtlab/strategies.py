"""Reusable Hypothesis strategies for this library's domain types.

Keeping generators in one module means tests and hunts agree on what a
"valid input" is, and a fix to a generator (say, widening the date window)
reaches every property at once.
"""

from __future__ import annotations

from datetime import date, timedelta

from hypothesis import strategies as st

from pbtlab.dateranges import DateRange

# A window with leap years, a century non-leap year (2100) and plenty of
# year boundaries, while keeping ranges short enough to iterate day by day.
MIN_DATE = date(2095, 1, 1)
MAX_DATE = date(2105, 12, 31)
MAX_SPAN_DAYS = 400

dates = st.dates(min_value=MIN_DATE, max_value=MAX_DATE)


@st.composite
def date_ranges(draw: st.DrawFn, *, allow_empty: bool = True) -> DateRange:
    """A ``DateRange`` inside the window, up to ``MAX_SPAN_DAYS`` long."""
    start = draw(dates)
    room = (MAX_DATE - start).days
    length = draw(
        st.integers(min_value=0 if allow_empty else 1, max_value=min(room, MAX_SPAN_DAYS))
    )
    return DateRange(start, start + timedelta(days=length))


@st.composite
def adjacent_pairs(draw: st.DrawFn) -> tuple[DateRange, DateRange]:
    """Two non-empty ranges where the first ends exactly where the second starts."""
    first = draw(date_ranges(allow_empty=False))
    room = (MAX_DATE - first.end).days
    length = draw(st.integers(min_value=1, max_value=max(1, min(room, MAX_SPAN_DAYS))))
    return first, DateRange(first.end, first.end + timedelta(days=length))


# Records whose sort key collides often, so stability is actually exercised.
# The second field is a unique tag recording original position.
def keyed_records(max_size: int = 50) -> st.SearchStrategy[list[tuple[int, int]]]:
    return st.lists(st.integers(min_value=0, max_value=5), max_size=max_size).map(
        lambda keys: [(k, tag) for tag, k in enumerate(keys)]
    )


_AWKWARD = "ab01\\"


@st.composite
def _runs(draw: st.DrawFn) -> str:
    """Text built from explicit runs, some long enough to need two-digit counts.

    Plain ``st.text()`` almost never repeats a character ten times in a row,
    so a decoder that only reads one count digit would sail through it.
    """
    pieces = draw(st.lists(st.tuples(st.sampled_from(_AWKWARD), st.integers(1, 15)), max_size=6))
    return "".join(ch * n for ch, n in pieces)


# Short text over an alphabet with digits and the escape character, long
# runs, and arbitrary Unicode: together they cover every encoder branch.
rle_text = st.text(alphabet=_AWKWARD, max_size=40) | _runs() | st.text(max_size=40)
