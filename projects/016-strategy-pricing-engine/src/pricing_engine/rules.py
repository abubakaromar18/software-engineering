"""Rules pair a condition with a strategy; conditions are composable predicates."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Generic, TypeVar

from .models import Cart

Condition = Callable[[Cart], bool]
S = TypeVar("S")


@dataclass(frozen=True, slots=True)
class Rule(Generic[S]):
    """When ``when`` holds, ``strategy`` is eligible. Lower priority runs first."""

    name: str
    when: Condition
    strategy: S
    priority: int = 100


def always(_cart: Cart) -> bool:
    return True


def all_of(*conditions: Condition) -> Condition:
    return lambda cart: all(condition(cart) for condition in conditions)


def any_of(*conditions: Condition) -> Condition:
    return lambda cart: any(condition(cart) for condition in conditions)


def negate(condition: Condition) -> Condition:
    return lambda cart: not condition(cart)


def tier_in(*tiers: str) -> Condition:
    return lambda cart: cart.customer_tier in tiers


def region_in(*regions: str) -> Condition:
    return lambda cart: cart.region in regions


def has_coupon(code: str) -> Condition:
    return lambda cart: cart.has_coupon(code)


def min_subtotal(amount: Decimal) -> Condition:
    return lambda cart: cart.subtotal >= amount


def date_between(start: date, end: date) -> Condition:
    """Inclusive at both ends."""
    return lambda cart: start <= cart.order_date <= end
