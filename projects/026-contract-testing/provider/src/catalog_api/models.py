"""Domain entities. Plain dataclasses keep the domain free of web-framework types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


@dataclass
class Product:
    id: str
    name: str
    category: str
    price_cents: int
    currency: str
    stock: int
    tags: list[str] = field(default_factory=list)
    # Present in the API response but no consumer depends on it. The contract
    # tests prove we are free to change or remove it (see test_contract_breakage).
    warehouse_location: str = "A-01"

    @property
    def in_stock(self) -> bool:
        return self.stock > 0


@dataclass(frozen=True)
class OrderLine:
    product_id: str
    quantity: int
    unit_price_cents: int

    @property
    def subtotal_cents(self) -> int:
        return self.quantity * self.unit_price_cents


class OrderStatus(StrEnum):
    PENDING = "PENDING"


@dataclass(frozen=True)
class Order:
    id: str
    lines: tuple[OrderLine, ...]
    currency: str
    status: OrderStatus
    created_at: datetime

    @property
    def total_cents(self) -> int:
        return sum(line.subtotal_cents for line in self.lines)
