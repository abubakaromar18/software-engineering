from __future__ import annotations

import pytest

from catalog_api.errors import InsufficientStock, InvalidOrder, ProductNotFound
from catalog_api.repository import InMemoryCatalogRepository
from catalog_api.service import CatalogService, OrderRequestLine
from tests.conftest import make_product
from tests.support import FIXED_NOW


def test_get_product_raises_for_unknown_id(service: CatalogService) -> None:
    with pytest.raises(ProductNotFound) as exc:
        service.get_product("P-404")
    assert exc.value.product_id == "P-404"


def test_list_products_filters_by_category(
    service: CatalogService, repo: InMemoryCatalogRepository
) -> None:
    repo.save_product(make_product(id="P-2", category="books"))
    repo.save_product(make_product(id="P-1", category="books"))
    repo.save_product(make_product(id="P-3", category="hardware"))

    assert [p.id for p in service.list_products("books")] == ["P-1", "P-2"]
    assert len(service.list_products()) == 3


def test_place_order_prices_lines_and_decrements_stock(
    service: CatalogService, repo: InMemoryCatalogRepository
) -> None:
    repo.save_product(make_product(id="P-1", price_cents=1000, stock=5))
    repo.save_product(make_product(id="P-2", price_cents=250, stock=5))

    order = service.place_order([OrderRequestLine("P-1", 2), OrderRequestLine("P-2", 4)])

    assert order.total_cents == 2 * 1000 + 4 * 250
    assert order.id == "ORD-00000001"
    assert order.created_at == FIXED_NOW
    assert repo.get_product("P-1").stock == 3  # type: ignore[union-attr]
    assert repo.get_order(order.id) == order


def test_place_order_is_all_or_nothing(
    service: CatalogService, repo: InMemoryCatalogRepository
) -> None:
    repo.save_product(make_product(id="P-1", stock=5))
    repo.save_product(make_product(id="P-2", stock=1))

    with pytest.raises(InsufficientStock):
        service.place_order([OrderRequestLine("P-1", 2), OrderRequestLine("P-2", 3)])

    assert repo.get_product("P-1").stock == 5  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "lines",
    [
        [],
        [OrderRequestLine("P-1", 0)],
        [OrderRequestLine("P-1", 101)],
        [OrderRequestLine("P-1", 1), OrderRequestLine("P-1", 1)],
    ],
    ids=["empty", "zero-qty", "too-many", "duplicate-line"],
)
def test_place_order_rejects_invalid_requests(
    service: CatalogService, repo: InMemoryCatalogRepository, lines: list[OrderRequestLine]
) -> None:
    repo.save_product(make_product(id="P-1"))
    with pytest.raises(InvalidOrder):
        service.place_order(lines)


def test_place_order_rejects_mixed_currencies(
    service: CatalogService, repo: InMemoryCatalogRepository
) -> None:
    repo.save_product(make_product(id="P-1", currency="USD"))
    repo.save_product(make_product(id="P-2", currency="EUR"))
    with pytest.raises(InvalidOrder, match="currency"):
        service.place_order([OrderRequestLine("P-1", 1), OrderRequestLine("P-2", 1)])
