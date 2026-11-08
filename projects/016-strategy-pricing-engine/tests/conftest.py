from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from pricing_engine.models import Cart, LineItem, PricedLine


def D(value: str) -> Decimal:  # noqa: N802 - conventional shorthand for Decimal
    return Decimal(value)


def item(sku="A", category="misc", price="10.00", quantity=1) -> LineItem:
    return LineItem(sku, category, Decimal(price), quantity)


def cart(*items: LineItem, **kwargs) -> Cart:
    kwargs.setdefault("order_date", date(2026, 6, 15))
    return Cart(items=items or (item(),), **kwargs)


def priced(*items: LineItem) -> Sequence[PricedLine]:
    return [PricedLine(i, i.gross) for i in items]
