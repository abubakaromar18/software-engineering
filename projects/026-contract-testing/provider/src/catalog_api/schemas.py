"""Wire format (DTOs). This module *is* the provider's half of the contract.

Field names are camelCase on the wire and snake_case in the domain; keeping the
translation here means a rename in the domain never leaks into the API by
accident - and if one does, Pact verification fails.
"""

from __future__ import annotations

from datetime import UTC

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from catalog_api.models import Order, Product


class WireModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ProductOut(WireModel):
    id: str
    name: str
    category: str
    price_cents: int
    currency: str
    in_stock: bool
    tags: list[str]
    warehouse_location: str

    @classmethod
    def from_domain(cls, product: Product) -> ProductOut:
        return cls(
            id=product.id,
            name=product.name,
            category=product.category,
            price_cents=product.price_cents,
            currency=product.currency,
            in_stock=product.in_stock,
            tags=list(product.tags),
            warehouse_location=product.warehouse_location,
        )


class ProductListOut(WireModel):
    items: list[ProductOut]
    count: int


class OrderLineIn(WireModel):
    product_id: str = Field(min_length=1)
    quantity: int


class OrderIn(WireModel):
    items: list[OrderLineIn]


class OrderLineOut(WireModel):
    product_id: str
    quantity: int
    unit_price_cents: int


class OrderOut(WireModel):
    id: str
    status: str
    items: list[OrderLineOut]
    total_cents: int
    currency: str
    created_at: str

    @classmethod
    def from_domain(cls, order: Order) -> OrderOut:
        return cls(
            id=order.id,
            status=order.status.value,
            items=[
                OrderLineOut(
                    product_id=line.product_id,
                    quantity=line.quantity,
                    unit_price_cents=line.unit_price_cents,
                )
                for line in order.lines
            ],
            total_cents=order.total_cents,
            currency=order.currency,
            # Second precision, always UTC with a "Z" suffix: the consumer's
            # contract pins this exact shape with a regex matcher.
            created_at=order.created_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )


class ErrorBody(WireModel):
    code: str
    message: str


class ErrorOut(WireModel):
    error: ErrorBody
