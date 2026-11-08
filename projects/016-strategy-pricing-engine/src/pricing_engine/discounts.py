"""Discount strategies: each returns one non-negative amount per input line.

Strategies are small, stateless and unaware of rules or of one another. The
engine decides when they run and clamps any amount above a line's net price.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from .errors import ConfigError, StrategyError
from .models import ZERO, PricedLine, allocate_pro_rata, percent_of, to_cents


class DiscountStrategy(Protocol):
    def discount(self, lines: Sequence[PricedLine]) -> list[Decimal]: ...


def _check_percent(percent: Decimal) -> None:
    if not 0 <= percent <= 100:
        raise ConfigError(f"percent must be between 0 and 100, got {percent}")


@dataclass(frozen=True, slots=True)
class PercentageOff:
    percent: Decimal

    def __post_init__(self) -> None:
        _check_percent(self.percent)

    def discount(self, lines: Sequence[PricedLine]) -> list[Decimal]:
        return [percent_of(line.net, self.percent) for line in lines]


@dataclass(frozen=True, slots=True)
class FixedAmountOff:
    """A fixed amount off the order, spread across lines by their net price."""

    amount: Decimal

    def __post_init__(self) -> None:
        if self.amount < 0 or self.amount != to_cents(self.amount):
            raise ConfigError(f"amount must be non-negative whole cents, got {self.amount}")

    def discount(self, lines: Sequence[PricedLine]) -> list[Decimal]:
        nets = [line.net for line in lines]
        return allocate_pro_rata(min(self.amount, sum(nets, ZERO)), nets)


@dataclass(frozen=True, slots=True)
class BuyXGetYFree:
    """For every complete group of X+Y units on a line, Y units are free."""

    buy: int
    free: int

    def __post_init__(self) -> None:
        if self.buy < 1 or self.free < 1:
            raise ConfigError("buy and free must both be at least 1")

    def discount(self, lines: Sequence[PricedLine]) -> list[Decimal]:
        return [self._line_discount(line) for line in lines]

    def _line_discount(self, line: PricedLine) -> Decimal:
        free_units = line.item.quantity // (self.buy + self.free) * self.free
        return to_cents(line.net * free_units / line.item.quantity)


@dataclass(frozen=True, slots=True)
class VolumeTiers:
    """Percentage off a line, set by the highest quantity tier that line reaches."""

    tiers: tuple[tuple[int, Decimal], ...]

    def __post_init__(self) -> None:
        if not self.tiers:
            raise ConfigError("volume tiers must not be empty")
        for min_quantity, percent in self.tiers:
            if min_quantity < 1:
                raise ConfigError("tier minimum quantity must be at least 1")
            _check_percent(percent)
        object.__setattr__(self, "tiers", tuple(sorted(self.tiers, reverse=True)))

    def discount(self, lines: Sequence[PricedLine]) -> list[Decimal]:
        return [percent_of(line.net, self._percent_for(line.item.quantity)) for line in lines]

    def _percent_for(self, quantity: int) -> Decimal:
        return next((pct for minimum, pct in self.tiers if quantity >= minimum), Decimal(0))


@dataclass(frozen=True, slots=True)
class CategoryScoped:
    """Decorator restricting any strategy to some categories.

    The inner strategy sees only in-scope lines, so a fixed amount is spread
    across those lines alone and other strategies need no scoping logic.
    """

    inner: DiscountStrategy
    categories: Collection[str]

    def discount(self, lines: Sequence[PricedLine]) -> list[Decimal]:
        indexes = [i for i, line in enumerate(lines) if line.item.category in self.categories]
        result = [ZERO] * len(lines)
        amounts = self.inner.discount([lines[i] for i in indexes])
        if len(amounts) != len(indexes):
            raise StrategyError(f"scoped strategy returned {len(amounts)} amounts")
        for index, amount in zip(indexes, amounts, strict=True):
            result[index] = amount
        return result
