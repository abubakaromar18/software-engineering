"""The context of the Strategy pattern: orchestrates rules, knows no pricing maths."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from decimal import Decimal

from .discounts import DiscountStrategy
from .errors import NoTaxRuleError, StrategyError
from .models import ZERO, Adjustment, Cart, PricedLine, Quote, QuoteLine
from .rules import Rule
from .stacking import Sequential, StackingPolicy, subtract
from .taxes import TaxStrategy


class PricingEngine:
    """Turns a cart into an itemised quote. Stateless, so safe to share between threads."""

    def __init__(
        self,
        discount_rules: Iterable[Rule[DiscountStrategy]],
        tax_rules: Iterable[Rule[TaxStrategy]],
        stacking: StackingPolicy | None = None,
    ) -> None:
        # sorted() is stable, so equal priorities keep their declared order.
        self._discount_rules = tuple(sorted(discount_rules, key=lambda rule: rule.priority))
        self._tax_rules = tuple(sorted(tax_rules, key=lambda rule: rule.priority))
        self._stacking = stacking if stacking is not None else Sequential()

    def quote(self, cart: Cart) -> Quote:
        original = [PricedLine(item, item.gross) for item in cart.items]
        eligible = [rule for rule in self._discount_rules if rule.when(cart)]

        discounted = original
        adjustments = []
        for applied in self._stacking.apply(eligible, original):
            discounted = subtract(discounted, applied)
            if applied.total > 0:
                adjustments.append(Adjustment(applied.rule, applied.total))

        tax_rule = self._select_tax_rule(cart)
        taxes = self._compute_tax(tax_rule, discounted)
        lines = tuple(
            QuoteLine(
                sku=line.item.sku,
                quantity=line.item.quantity,
                gross=line.item.gross,
                discount=line.item.gross - line.net,
                net=line.net,
                tax=tax,
            )
            for line, tax in zip(discounted, taxes, strict=True)
        )
        return Quote(lines=lines, discounts=tuple(adjustments), tax_rule=tax_rule.name)

    def _select_tax_rule(self, cart: Cart) -> Rule[TaxStrategy]:
        """Unlike discounts, exactly one tax rule applies: the first that matches."""
        for rule in self._tax_rules:
            if rule.when(cart):
                return rule
        raise NoTaxRuleError(f"no tax rule matches region {cart.region!r}")

    @staticmethod
    def _compute_tax(rule: Rule[TaxStrategy], lines: Sequence[PricedLine]) -> list[Decimal]:
        taxes = rule.strategy.tax(lines)
        if len(taxes) != len(lines):
            raise StrategyError(f"{rule.name}: got {len(taxes)} amounts for {len(lines)} lines")
        if any(tax < ZERO for tax in taxes):
            raise StrategyError(f"{rule.name}: returned a negative tax")
        return taxes
