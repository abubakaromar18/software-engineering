"""Daily update rules, one small class per kind of item.

Each rule answers a single question — "how does *this kind* of item change in
one day?" — so the business rules read like the requirements document instead
of a nest of ``if`` statements.

Two helpers, :func:`raise_quality` and :func:`lower_quality`, encode the bounds
exactly as the legacy code applied them. Note the subtle legacy semantics they
preserve: bounds are enforced *as a step limit*, not as a clamp. An item that
somehow starts above 50 is never pulled down to 50, and one below 0 is never
pushed up to 0 — it simply stops moving in that direction.
"""

from typing import Protocol

from gilded_rose.item import Item

MAX_QUALITY = 50
MIN_QUALITY = 0

# Backstage pass thresholds: quality rises faster as the concert approaches.
BACKSTAGE_DOUBLE_WITHIN_DAYS = 10
BACKSTAGE_TRIPLE_WITHIN_DAYS = 5


def raise_quality(item: Item, amount: int = 1) -> None:
    """Increase quality by ``amount`` without crossing MAX_QUALITY."""
    if item.quality < MAX_QUALITY:
        item.quality = min(MAX_QUALITY, item.quality + amount)


def lower_quality(item: Item, amount: int = 1) -> None:
    """Decrease quality by ``amount`` without crossing MIN_QUALITY."""
    if item.quality > MIN_QUALITY:
        item.quality = max(MIN_QUALITY, item.quality - amount)


def age(item: Item) -> None:
    """One day passes: the sell-by date gets one day closer."""
    item.sell_in -= 1


def is_expired(item: Item) -> bool:
    return item.sell_in < 0


class UpdateRule(Protocol):
    """Strategy interface: mutate one item to reflect the passing of one day."""

    def update(self, item: Item) -> None: ...


class StandardRule:
    """Ordinary goods lose 1 quality a day, 2 a day once past their sell-by date."""

    def __init__(self, degradation: int = 1) -> None:
        self._degradation = degradation

    def update(self, item: Item) -> None:
        age(item)
        multiplier = 2 if is_expired(item) else 1
        lower_quality(item, self._degradation * multiplier)


class ConjuredRule(StandardRule):
    """Conjured goods degrade twice as fast as standard goods (the new feature)."""

    def __init__(self) -> None:
        super().__init__(degradation=2)


class AgedBrieRule:
    """Aged Brie improves with age, twice as fast once past its sell-by date."""

    def update(self, item: Item) -> None:
        age(item)
        raise_quality(item, 2 if is_expired(item) else 1)


class BackstagePassRule:
    """Passes gain value as the concert nears, then become worthless after it."""

    def update(self, item: Item) -> None:
        # The bonus depends on the days remaining *before* today's aging.
        if item.sell_in <= BACKSTAGE_TRIPLE_WITHIN_DAYS:
            bonus = 3
        elif item.sell_in <= BACKSTAGE_DOUBLE_WITHIN_DAYS:
            bonus = 2
        else:
            bonus = 1
        raise_quality(item, bonus)
        age(item)
        if is_expired(item):
            item.quality = 0


class LegendaryRule:
    """Legendary items never have to be sold and never change."""

    def update(self, item: Item) -> None:
        return None
