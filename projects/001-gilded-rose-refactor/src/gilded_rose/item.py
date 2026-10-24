"""The Item class, owned by "the goblin in the corner".

Kata constraint: this class (and the ``items`` attribute of the inventory) must
not be changed. Every refactoring step therefore works *around* it rather than
adding behaviour to it — which is why the update rules live in their own module
instead of becoming methods on ``Item``.
"""


class Item:
    def __init__(self, name: str, sell_in: int, quality: int) -> None:
        self.name = name
        self.sell_in = sell_in
        self.quality = quality

    def __repr__(self) -> str:
        return f"{self.name}, {self.sell_in}, {self.quality}"
