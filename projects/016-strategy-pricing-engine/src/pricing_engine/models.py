"""Immutable domain types and the money arithmetic they rely on.

All amounts are ``Decimal`` in a single implied currency, rounded to cents.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .errors import InvalidCartError

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def to_cents(amount: Decimal) -> Decimal:
    """Round to cents, half up (the convention on most retail receipts)."""
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def percent_of(base: Decimal, percent: Decimal) -> Decimal:
    return to_cents(base * percent / 100)


def allocate_pro_rata(amount: Decimal, weights: Sequence[Decimal]) -> list[Decimal]:
    """Split ``amount`` across ``weights`` so the parts sum to it exactly.

    Uses the largest-remainder method on integer cents: naive per-line rounding
    can gain or lose a cent. Ties go to the earliest line, keeping it deterministic.
    """
    total_cents = sum(_as_cents(w) for w in weights)
    if total_cents == 0:
        return [ZERO for _ in weights]

    amount_cents = _as_cents(amount)
    shares = [divmod(amount_cents * _as_cents(w), total_cents) for w in weights]
    parts = [quotient for quotient, _ in shares]
    leftover = amount_cents - sum(parts)
    by_remainder = sorted(range(len(shares)), key=lambda i: (-shares[i][1], i))
    for index in by_remainder[:leftover]:
        parts[index] += 1
    return [Decimal(part) * CENT for part in parts]


def _as_cents(amount: Decimal) -> int:
    return int(to_cents(amount) / CENT)


@dataclass(frozen=True, slots=True)
class LineItem:
    sku: str
    category: str
    unit_price: Decimal
    quantity: int

    def __post_init__(self) -> None:
        if not self.sku or not isinstance(self.sku, str):
            raise InvalidCartError("line item needs a non-empty string sku")
        if not isinstance(self.category, str):
            raise InvalidCartError(f"{self.sku}: category must be a string")
        if not isinstance(self.unit_price, Decimal) or not self.unit_price.is_finite():
            raise InvalidCartError(f"{self.sku}: unit_price must be a finite Decimal")
        if self.unit_price < 0 or self.unit_price != to_cents(self.unit_price):
            raise InvalidCartError(f"{self.sku}: unit_price must be non-negative whole cents")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int):
            raise InvalidCartError(f"{self.sku}: quantity must be an integer")
        if self.quantity <= 0:
            raise InvalidCartError(f"{self.sku}: quantity must be positive")

    @property
    def gross(self) -> Decimal:
        return to_cents(self.unit_price * self.quantity)


@dataclass(frozen=True, slots=True)
class Cart:
    """Everything rules may inspect. The date is an input so pricing stays pure."""

    items: tuple[LineItem, ...]
    order_date: date
    region: str = ""
    customer_tier: str = "standard"
    coupons: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.items:
            raise InvalidCartError("cart must contain at least one item")
        skus = [item.sku for item in self.items]
        if len(set(skus)) != len(skus):
            raise InvalidCartError("cart contains duplicate skus; merge them into one line")
        object.__setattr__(self, "coupons", frozenset(c.upper() for c in self.coupons))

    @property
    def subtotal(self) -> Decimal:
        return sum((item.gross for item in self.items), ZERO)

    def has_coupon(self, code: str) -> bool:
        return code.upper() in self.coupons


@dataclass(frozen=True, slots=True)
class PricedLine:
    """A cart line and its price after the discounts applied so far."""

    item: LineItem
    net: Decimal


@dataclass(frozen=True, slots=True)
class Adjustment:
    """One rule's contribution, kept so a quote can explain itself."""

    rule: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class QuoteLine:
    sku: str
    quantity: int
    gross: Decimal
    discount: Decimal
    net: Decimal
    tax: Decimal

    @property
    def total(self) -> Decimal:
        return self.net + self.tax


@dataclass(frozen=True, slots=True)
class Quote:
    lines: tuple[QuoteLine, ...]
    discounts: tuple[Adjustment, ...]
    tax_rule: str

    @property
    def subtotal(self) -> Decimal:
        return sum((line.gross for line in self.lines), ZERO)

    @property
    def discount_total(self) -> Decimal:
        return sum((line.discount for line in self.lines), ZERO)

    @property
    def tax_total(self) -> Decimal:
        return sum((line.tax for line in self.lines), ZERO)

    @property
    def total(self) -> Decimal:
        return self.subtotal - self.discount_total + self.tax_total

    def to_dict(self) -> dict[str, Any]:
        """JSON-friendly form; amounts are strings so no precision is lost."""
        return {
            "lines": [
                {
                    "sku": line.sku,
                    "quantity": line.quantity,
                    "gross": str(line.gross),
                    "discount": str(line.discount),
                    "net": str(line.net),
                    "tax": str(line.tax),
                    "total": str(line.total),
                }
                for line in self.lines
            ],
            "discounts": [{"rule": d.rule, "amount": str(d.amount)} for d in self.discounts],
            "tax_rule": self.tax_rule,
            "subtotal": str(self.subtotal),
            "discount_total": str(self.discount_total),
            "tax_total": str(self.tax_total),
            "total": str(self.total),
        }
