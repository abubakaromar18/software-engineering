"""Text-based simulation used both by the CLI and the golden-master test."""

from typing import Callable, Iterator, List, Protocol

from gilded_rose.item import Item


class Inventory(Protocol):
    items: List[Item]

    def update_quality(self) -> None: ...


def sample_items() -> List[Item]:
    """The classic kata fixture: one or more of every kind of item."""
    return [
        Item(name="+5 Dexterity Vest", sell_in=10, quality=20),
        Item(name="Aged Brie", sell_in=2, quality=0),
        Item(name="Elixir of the Mongoose", sell_in=5, quality=7),
        Item(name="Sulfuras, Hand of Ragnaros", sell_in=0, quality=80),
        Item(name="Sulfuras, Hand of Ragnaros", sell_in=-1, quality=80),
        Item(name="Backstage passes to a TAFKAL80ETC concert", sell_in=15, quality=20),
        Item(name="Backstage passes to a TAFKAL80ETC concert", sell_in=10, quality=49),
        Item(name="Backstage passes to a TAFKAL80ETC concert", sell_in=5, quality=49),
        Item(name="Conjured Mana Cake", sell_in=3, quality=6),
    ]


def simulate(factory: Callable[[List[Item]], Inventory], days: int) -> Iterator[str]:
    """Yield a human-readable report line by line, starting with day 0."""
    if days < 0:
        raise ValueError(f"days must be non-negative, got {days}")
    inventory = factory(sample_items())
    for day in range(days + 1):
        yield f"-------- day {day} --------"
        yield "name, sellIn, quality"
        for item in inventory.items:
            yield repr(item)
        yield ""
        inventory.update_quality()
