"""Provider-state handlers: the provider's side of every ``given(...)`` clause.

Each consumer interaction names a state such as "a product with id exists" and
passes parameters. Before the interaction is replayed, Pact calls the matching
handler here to put the provider's store into that state. Handlers talk to the
repository directly - they set up *data*, they don't go through the API.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from catalog_api.models import Product
from catalog_api.repository import InMemoryCatalogRepository

Action = Literal["setup", "teardown"]
Handler = Callable[[Action, dict[str, Any] | None], None]

# NOTE: pact-python binds handler arguments *by name*, so every handler must
# name them exactly ``action`` and ``parameters``.


def build_state_handlers(repo: InMemoryCatalogRepository) -> dict[str, Handler]:
    def _book(product_id: str, *, stock: int = 10, name: str | None = None) -> Product:
        return Product(
            id=product_id,
            name=name or f"Book {product_id}",
            category="books",
            price_cents=4599,
            currency="USD",
            stock=stock,
            tags=["databases"],
        )

    def product_exists(action: Action, parameters: dict[str, Any] | None) -> None:
        if action == "setup":
            repo.save_product(_book(_param(parameters, "id")))

    def product_missing(action: Action, parameters: dict[str, Any] | None) -> None:
        if action == "setup":
            assert repo.get_product(_param(parameters, "id")) is None

    def products_in_category(action: Action, parameters: dict[str, Any] | None) -> None:
        if action == "setup":
            category = _param(parameters, "category")
            repo.save_product(_book("P-100"))
            repo.save_product(_book("P-101", name="The Pragmatic Programmer"))
            repo.save_product(Product("P-200", "Keyboard", "hardware", 12900, "USD", 1))
            assert repo.list_products(category), f"no seed data for {category!r}"

    def limited_stock(action: Action, parameters: dict[str, Any] | None) -> None:
        if action == "setup":
            repo.save_product(
                _book(_param(parameters, "id"), stock=int(_param(parameters, "stock")))
            )

    def reset(action: Action, parameters: dict[str, Any] | None) -> None:
        # The "" key is Pact's generic hook, run around every interaction.
        if action == "teardown":
            repo.clear()

    return {
        "": reset,
        "a product with id exists": product_exists,
        "no product with id exists": product_missing,
        "products exist in category": products_in_category,
        "a product has limited stock": limited_stock,
    }


def _param(params: dict[str, Any] | None, name: str) -> Any:
    if not params or name not in params:
        raise ValueError(f"provider state is missing required parameter {name!r}")
    return params[name]
