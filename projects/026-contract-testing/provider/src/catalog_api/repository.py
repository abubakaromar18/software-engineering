"""Storage port and an in-memory adapter.

The service depends on the ``CatalogRepository`` protocol, not on a concrete
store. Provider-state handlers in the contract tests seed the in-memory
implementation directly, which is what makes verification fast and
deterministic.
"""

from __future__ import annotations

from threading import Lock
from typing import Protocol

from catalog_api.models import Order, Product


class CatalogRepository(Protocol):
    def get_product(self, product_id: str) -> Product | None: ...
    def list_products(self, category: str | None = None) -> list[Product]: ...
    def save_product(self, product: Product) -> None: ...
    def save_order(self, order: Order) -> None: ...
    def get_order(self, order_id: str) -> Order | None: ...
    def clear(self) -> None: ...


class InMemoryCatalogRepository:
    """Thread-safe dict-backed repository (uvicorn serves from a worker thread)."""

    def __init__(self, products: list[Product] | None = None) -> None:
        self._lock = Lock()
        self._products: dict[str, Product] = {p.id: p for p in products or []}
        self._orders: dict[str, Order] = {}

    def get_product(self, product_id: str) -> Product | None:
        with self._lock:
            return self._products.get(product_id)

    def list_products(self, category: str | None = None) -> list[Product]:
        with self._lock:
            products = sorted(self._products.values(), key=lambda p: p.id)
        if category is None:
            return products
        return [p for p in products if p.category == category]

    def save_product(self, product: Product) -> None:
        with self._lock:
            self._products[product.id] = product

    def save_order(self, order: Order) -> None:
        with self._lock:
            self._orders[order.id] = order

    def get_order(self, order_id: str) -> Order | None:
        with self._lock:
            return self._orders.get(order_id)

    def clear(self) -> None:
        with self._lock:
            self._products.clear()
            self._orders.clear()


def demo_products() -> list[Product]:
    """Seed data used when the API is run locally."""
    return [
        Product(
            "P-100",
            "Designing Data-Intensive Applications",
            "books",
            4599,
            "USD",
            12,
            ["distributed-systems", "databases"],
            "B-04",
        ),
        Product("P-101", "The Pragmatic Programmer", "books", 3999, "USD", 3, ["craft"], "B-04"),
        Product(
            "P-200", "Mechanical Keyboard", "hardware", 12900, "USD", 0, ["peripherals"], "H-11"
        ),
    ]
