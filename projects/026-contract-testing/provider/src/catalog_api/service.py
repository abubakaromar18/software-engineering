"""Application service: the business rules, independent of HTTP."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from catalog_api.errors import InsufficientStock, InvalidOrder, ProductNotFound
from catalog_api.models import Order, OrderLine, OrderStatus, Product
from catalog_api.repository import CatalogRepository

Clock = Callable[[], datetime]
IdGenerator = Callable[[], str]

MAX_QUANTITY_PER_LINE = 100


def utc_now() -> datetime:
    return datetime.now(UTC)


def random_order_id() -> str:
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


@dataclass(frozen=True)
class OrderRequestLine:
    product_id: str
    quantity: int


class CatalogService:
    """Reads the catalog and places orders.

    Time and id generation are injected so tests (including contract tests) get
    deterministic output without monkey-patching.
    """

    def __init__(
        self,
        repository: CatalogRepository,
        clock: Clock = utc_now,
        id_generator: IdGenerator = random_order_id,
    ) -> None:
        self._repo = repository
        self._clock = clock
        self._next_id = id_generator

    def get_product(self, product_id: str) -> Product:
        product = self._repo.get_product(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        return product

    def list_products(self, category: str | None = None) -> list[Product]:
        return self._repo.list_products(category)

    def place_order(self, request_lines: list[OrderRequestLine]) -> Order:
        """Validate all lines first, then reserve stock - all or nothing."""
        if not request_lines:
            raise InvalidOrder("An order needs at least one item")

        seen: set[str] = set()
        priced: list[tuple[Product, int]] = []
        for line in request_lines:
            if not 1 <= line.quantity <= MAX_QUANTITY_PER_LINE:
                raise InvalidOrder(
                    f"Quantity for {line.product_id} must be between 1 and {MAX_QUANTITY_PER_LINE}"
                )
            if line.product_id in seen:
                raise InvalidOrder(f"Product {line.product_id} appears more than once")
            seen.add(line.product_id)
            product = self.get_product(line.product_id)
            if product.stock < line.quantity:
                raise InsufficientStock(product.id, line.quantity, product.stock)
            priced.append((product, line.quantity))

        currencies = {product.currency for product, _ in priced}
        if len(currencies) > 1:
            raise InvalidOrder("All items in an order must share one currency")

        for product, quantity in priced:
            product.stock -= quantity
            self._repo.save_product(product)

        order = Order(
            id=self._next_id(),
            lines=tuple(OrderLine(p.id, q, p.price_cents) for p, q in priced),
            currency=currencies.pop(),
            status=OrderStatus.PENDING,
            created_at=self._clock(),
        )
        self._repo.save_order(order)
        return order
