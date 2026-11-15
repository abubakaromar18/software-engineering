"""Bug hunts: point a property at a buggy specimen and let Hypothesis shrink.

A :class:`Hunt` pairs one *law* (a property any correct implementation
obeys) with a buggy specimen and the real implementation. The same law is
used both ways, which is what makes the result trustworthy:

* against the specimen, Hypothesis must find a counterexample, and
* against the real code, the identical law must hold.

Run ``python -m pbtlab.hunts`` (or ``pbtlab-hunt``) to see the minimal
counterexample Hypothesis finds for each specimen.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from hypothesis import HealthCheck, Phase, find, settings
from hypothesis import strategies as st
from hypothesis.errors import NoSuchExample

from pbtlab import dateranges, encoding, sorting, specimens
from pbtlab import strategies as pst

Law = Callable[[Any, Any], bool]
"""``law(implementation, example) -> True`` when the property holds."""


@dataclass(frozen=True)
class Hunt:
    name: str
    law_text: str
    strategy: st.SearchStrategy[Any]
    law: Law
    buggy: Any
    correct: Any

    def holds(self, implementation: Any, example: Any) -> bool:
        """Evaluate the law, treating any exception as a violation."""
        try:
            return bool(self.law(implementation, example))
        except Exception:
            return False


@dataclass(frozen=True)
class HuntResult:
    hunt: Hunt
    counterexample: Any | None

    @property
    def caught(self) -> bool:
        return self.counterexample is not None


# ------------------------------------------------------------------ laws


def _first(record: tuple[int, int]) -> int:
    return record[0]


def _is_stable_sort(impl: Callable, records: list[tuple[int, int]]) -> bool:
    return impl(records, key=_first) == sorted(records, key=_first)


def _is_permutation(impl: Callable, xs: list[int]) -> bool:
    return Counter(impl(xs)) == Counter(xs)


def _round_trips(codec: tuple[Callable[[str], str], Callable[[str], str]], text: str) -> bool:
    encode, decode = codec
    return decode(encode(text)) == text


def _zigzag_inverts(impl: Callable[[int], int], n: int) -> bool:
    z = impl(n)
    return z >= 0 and encoding.unzigzag(z) == n


def _overlap_means_shared_day(
    impl: Callable, pair: tuple[dateranges.DateRange, dateranges.DateRange]
) -> bool:
    a, b = pair
    return impl(a, b) == any(day in b for day in a)


def _merge_is_canonical_union(impl: Callable, ranges: list[dateranges.DateRange]) -> bool:
    out = impl(ranges)
    canonical = all(r.days > 0 for r in out) and all(
        x.end < y.start for x, y in zip(out, out[1:], strict=False)
    )
    same_days = {d for r in out for d in r} == {d for r in ranges for d in r}
    return canonical and same_days


def _split_reassembles(impl: Callable, span: dateranges.DateRange) -> bool:
    pieces = list(impl(span))
    days = [d for p in pieces for d in p]
    one_month_each = all(
        not p.is_empty and p.end <= dateranges.first_of_next_month(p.start) for p in pieces
    )
    return days == list(span) and one_month_each


# ----------------------------------------------------------------- hunts

_range_pairs = st.tuples(pst.date_ranges(), pst.date_ranges()) | pst.adjacent_pairs()

HUNTS: tuple[Hunt, ...] = (
    Hunt(
        name="merge_sort_unstable",
        law_text="sorting by key keeps equal keys in input order",
        strategy=pst.keyed_records(),
        law=_is_stable_sort,
        buggy=specimens.merge_sort_unstable,
        correct=sorting.merge_sort,
    ),
    Hunt(
        name="merge_sort_drops_tail",
        law_text="output is a permutation of the input",
        strategy=st.lists(st.integers()),
        law=_is_permutation,
        buggy=specimens.merge_sort_drops_tail,
        correct=sorting.merge_sort,
    ),
    Hunt(
        name="rle_naive",
        law_text="decode(encode(s)) == s",
        strategy=pst.rle_text,
        law=_round_trips,
        buggy=(specimens.rle_encode_naive, specimens.rle_decode_naive),
        correct=(encoding.rle_encode, encoding.rle_decode),
    ),
    Hunt(
        name="rle_decode_single_digit",
        law_text="decode(encode(s)) == s",
        strategy=pst.rle_text,
        law=_round_trips,
        buggy=(encoding.rle_encode, specimens.rle_decode_single_digit),
        correct=(encoding.rle_encode, encoding.rle_decode),
    ),
    Hunt(
        name="zigzag_fixed64",
        law_text="zigzag(n) >= 0 and unzigzag(zigzag(n)) == n",
        strategy=st.integers(),
        law=_zigzag_inverts,
        buggy=specimens.zigzag_fixed64,
        correct=encoding.zigzag,
    ),
    Hunt(
        name="overlaps_inclusive",
        law_text="a.overlaps(b) iff some day is in both",
        strategy=_range_pairs,
        law=_overlap_means_shared_day,
        buggy=specimens.overlaps_inclusive,
        correct=dateranges.DateRange.overlaps,
    ),
    Hunt(
        name="merge_without_sorting",
        law_text="merge() is sorted, disjoint, non-touching and covers the same days",
        strategy=st.lists(pst.date_ranges(), max_size=6),
        law=_merge_is_canonical_union,
        buggy=specimens.merge_without_sorting,
        correct=dateranges.merge,
    ),
    Hunt(
        name="split_by_month_naive",
        law_text="month pieces concatenate back to the original range",
        strategy=pst.date_ranges(),
        law=_split_reassembles,
        buggy=specimens.split_by_month_naive,
        correct=dateranges.split_by_month,
    ),
)


def run_hunt(hunt: Hunt, *, max_examples: int = 2000) -> HuntResult:
    """Search for a minimal example on which the buggy specimen breaks the law."""
    config = settings(
        max_examples=max_examples,
        database=None,  # fresh search every time, so the demo is honest
        deadline=None,
        phases=[Phase.generate, Phase.shrink],
        suppress_health_check=list(HealthCheck),
    )
    try:
        example = find(hunt.strategy, lambda x: not hunt.holds(hunt.buggy, x), settings=config)
    except NoSuchExample:
        return HuntResult(hunt, None)
    return HuntResult(hunt, example)


def _format(result: HuntResult) -> str:
    hunt = result.hunt
    if not result.caught:
        return f"[missed] {hunt.name}: no counterexample for '{hunt.law_text}'"
    return (
        f"[caught] {hunt.name}\n"
        f"         law:  {hunt.law_text}\n"
        f"         min:  {result.counterexample!r}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*", help="hunts to run (default: all)")
    parser.add_argument("--max-examples", type=int, default=2000)
    parser.add_argument("--list", action="store_true", help="list hunt names and exit")
    args = parser.parse_args(argv)

    by_name = {h.name: h for h in HUNTS}
    if args.list:
        for hunt in HUNTS:
            print(f"{hunt.name:26} {hunt.law_text}")
        return 0
    unknown = [n for n in args.names if n not in by_name]
    if unknown:
        parser.error(f"unknown hunt(s): {', '.join(unknown)}")

    selected = [by_name[n] for n in args.names] or list(HUNTS)
    results = [run_hunt(h, max_examples=args.max_examples) for h in selected]
    for result in results:
        print(_format(result))
    caught = sum(r.caught for r in results)
    print(f"\n{caught}/{len(results)} specimens caught")
    return 0 if caught == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
