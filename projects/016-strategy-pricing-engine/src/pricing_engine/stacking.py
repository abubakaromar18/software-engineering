"""Stacking policies: how several eligible discounts combine."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Protocol

from .discounts import DiscountStrategy
from .errors import StrategyError
from .models import PricedLine
from .rules import Rule


@dataclass(frozen=True, slots=True)
class AppliedDiscount:
    rule: str
    amounts: tuple[Decimal, ...]

    @property
    def total(self) -> Decimal:
        return sum(self.amounts, Decimal("0.00"))


class StackingPolicy(Protocol):
    def apply(
        self, rules: Sequence[Rule[DiscountStrategy]], lines: Sequence[PricedLine]
    ) -> list[AppliedDiscount]: ...


def run_discount(rule: Rule[DiscountStrategy], lines: Sequence[PricedLine]) -> AppliedDiscount:
    """Run one strategy, enforcing its contract and capping each line at its net."""
    amounts = rule.strategy.discount(lines)
    if len(amounts) != len(lines):
        raise StrategyError(f"{rule.name}: returned {len(amounts)} amounts for {len(lines)} lines")
    if any(amount < 0 for amount in amounts):
        raise StrategyError(f"{rule.name}: returned a negative discount")
    capped = tuple(min(amount, line.net) for amount, line in zip(amounts, lines, strict=True))
    return AppliedDiscount(rule.name, capped)


def subtract(lines: Sequence[PricedLine], applied: AppliedDiscount) -> list[PricedLine]:
    return [
        replace(line, net=line.net - amount)
        for line, amount in zip(lines, applied.amounts, strict=True)
    ]


class Sequential:
    """Apply every rule in priority order, each on the price left by the last."""

    def apply(
        self, rules: Sequence[Rule[DiscountStrategy]], lines: Sequence[PricedLine]
    ) -> list[AppliedDiscount]:
        applied = []
        current = list(lines)
        for rule in rules:
            result = run_discount(rule, current)
            applied.append(result)
            current = subtract(current, result)
        return applied


class BestForCustomer:
    """Apply only the single largest discount; ties go to the higher-priority rule."""

    def apply(
        self, rules: Sequence[Rule[DiscountStrategy]], lines: Sequence[PricedLine]
    ) -> list[AppliedDiscount]:
        results = [run_discount(rule, lines) for rule in rules]
        return [max(results, key=lambda result: result.total)] if results else []
