"""Domain errors. Each maps to exactly one HTTP status and machine-readable code."""

from __future__ import annotations


class CatalogError(Exception):
    """Base class for errors that are safe to expose to API clients."""

    status_code: int = 500
    code: str = "INTERNAL"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ProductNotFound(CatalogError):
    status_code = 404
    code = "NOT_FOUND"

    def __init__(self, product_id: str) -> None:
        super().__init__(f"Product {product_id} does not exist")
        self.product_id = product_id


class InsufficientStock(CatalogError):
    status_code = 409
    code = "INSUFFICIENT_STOCK"

    def __init__(self, product_id: str, requested: int, available: int) -> None:
        super().__init__(f"Requested {requested} of {product_id} but only {available} in stock")
        self.product_id = product_id
        self.requested = requested
        self.available = available


class InvalidOrder(CatalogError):
    status_code = 422
    code = "INVALID_ORDER"
