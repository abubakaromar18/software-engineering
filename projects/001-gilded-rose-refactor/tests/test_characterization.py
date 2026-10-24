"""Characterization tests: the refactored code must behave exactly like legacy.

These tests make no claims about what the behaviour *should* be — they pin what
it *is*. That is what made the refactor safe: every step could be checked
against the oracle in :mod:`gilded_rose.legacy`.

Conjured items are excluded on purpose: legacy treats them as ordinary goods,
and the refactor intentionally changes that (see ``test_rules.py``).
"""

import itertools

from hypothesis import given, settings
from hypothesis import strategies as st

from gilded_rose.inventory import AGED_BRIE, BACKSTAGE_PASS, CONJURED_PREFIX, SULFURAS, GildedRose
from gilded_rose.item import Item
from gilded_rose.legacy import LegacyGildedRose

KNOWN_NAMES = [AGED_BRIE, BACKSTAGE_PASS, SULFURAS, "+5 Dexterity Vest", "Elixir of the Mongoose"]


def snapshot(items):
    return [(item.name, item.sell_in, item.quality) for item in items]


def run_both(item_specs, days):
    legacy = LegacyGildedRose([Item(*spec) for spec in item_specs])
    refactored = GildedRose([Item(*spec) for spec in item_specs])
    for _ in range(days):
        legacy.update_quality()
        refactored.update_quality()
    return snapshot(legacy.items), snapshot(refactored.items)


def test_exhaustive_grid_over_boundaries_matches_legacy():
    # Every boundary the legacy code cares about: sell_in around 0/5/10 and
    # quality around 0/50, including out-of-range starting values.
    sell_ins = range(-2, 13)
    qualities = [-1, 0, 1, 2, 3, 47, 48, 49, 50, 51, 80]
    for name, sell_in, quality in itertools.product(KNOWN_NAMES, sell_ins, qualities):
        for days in (1, 2, 12):
            legacy, refactored = run_both([(name, sell_in, quality)], days)
            assert refactored == legacy, (name, sell_in, quality, days)


item_names = st.one_of(
    st.sampled_from(KNOWN_NAMES),
    st.text(min_size=0, max_size=20).filter(lambda s: not s.startswith(CONJURED_PREFIX)),
)
item_specs = st.tuples(item_names, st.integers(-20, 30), st.integers(-10, 90))


@settings(max_examples=400, deadline=None)
@given(specs=st.lists(item_specs, min_size=1, max_size=8), days=st.integers(0, 40))
def test_random_inventories_match_legacy(specs, days):
    legacy, refactored = run_both(specs, days)
    assert refactored == legacy
