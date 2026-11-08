"""Tax strategies: each returns one non-negative amount per discounted line."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from .errors import ConfigError
from .models import ZERO, PricedLine, percent_of


class TaxStrategy(Protocol):
    def tax(self, lines: Sequence[PricedLine]) -> list[Decimal]: ...


def _check_rate(rate: Decimal) -> None:
    if rate < 0:
        raise ConfigError(f"tax rate must not be negative, got {rate}")


@dataclass(frozen=True, slots=True)
class NoTax:
    """Explicit exemption: a deliberate rule, unlike simply matching nothing."""

    def tax(self, lines: Sequence[PricedLine]) -> list[Decimal]:
        return [ZERO for _ in lines]


@dataclass(frozen=True, slots=True)
class FlatRateTax:
    rate: Decimal

    def __post_init__(self) -> None:
        _check_rate(self.rate)

    def tax(self, lines: Sequence[PricedLine]) -> list[Decimal]:
        return [percent_of(line.net, self.rate) for line in lines]


@dataclass(frozen=True, slots=True)
class CategoryRateTax:
    """A default rate with per-category overrides, e.g. zero-rated groceries."""

    default: Decimal
    rates: Mapping[str, Decimal]

    def __post_init__(self) -> None:
        _check_rate(self.default)
        for rate in self.rates.values():
            _check_rate(rate)

    def tax(self, lines: Sequence[PricedLine]) -> list[Decimal]:
        return [
            percent_of(line.net, self.rates.get(line.item.category, self.default))
            for line in lines
        ]
