"""The refactored inventory: pick a rule for each item, then apply it.

Rule selection is data, not control flow. Adding a new kind of item means
adding one rule class and one entry to the catalog — no existing branch is
edited (the Open/Closed Principle in its most practical form).
"""

from typing import Callable, List, Optional, Sequence, Tuple

from gilded_rose.item import Item
from gilded_rose.rules import (
    AgedBrieRule,
    BackstagePassRule,
    ConjuredRule,
    LegendaryRule,
    StandardRule,
    UpdateRule,
)

AGED_BRIE = "Aged Brie"
BACKSTAGE_PASS = "Backstage passes to a TAFKAL80ETC concert"
SULFURAS = "Sulfuras, Hand of Ragnaros"
CONJURED_PREFIX = "Conjured"

Matcher = Callable[[str], bool]


def named(name: str) -> Matcher:
    """Match one exact item name (the legacy code matched exact names only)."""
    return lambda candidate: candidate == name


def prefixed(prefix: str) -> Matcher:
    """Match any item whose name starts with ``prefix``."""
    return lambda candidate: candidate.startswith(prefix)


# Ordered: the first matching entry wins, so specific matchers go first.
DEFAULT_CATALOG: Tuple[Tuple[Matcher, UpdateRule], ...] = (
    (named(SULFURAS), LegendaryRule()),
    (named(AGED_BRIE), AgedBrieRule()),
    (named(BACKSTAGE_PASS), BackstagePassRule()),
    (prefixed(CONJURED_PREFIX), ConjuredRule()),
)


class RuleBook:
    """Resolves the update rule for an item name, with a fallback default."""

    def __init__(
        self,
        catalog: Sequence[Tuple[Matcher, UpdateRule]] = DEFAULT_CATALOG,
        default: Optional[UpdateRule] = None,
    ) -> None:
        self._catalog = tuple(catalog)
        self._default = default if default is not None else StandardRule()

    def rule_for(self, item: Item) -> UpdateRule:
        for matches, rule in self._catalog:
            if matches(item.name):
                return rule
        return self._default


class GildedRose:
    """Same public interface as the legacy class: ``items`` + ``update_quality``."""

    def __init__(self, items: List[Item], rule_book: Optional[RuleBook] = None) -> None:
        self.items = items
        self._rules = rule_book if rule_book is not None else RuleBook()

    def update_quality(self) -> None:
        for item in self.items:
            self._rules.rule_for(item).update(item)
