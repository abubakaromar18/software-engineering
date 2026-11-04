"""Exception hierarchy exposed by the facade.

Callers catch these instead of inspecting vendor return codes. Each carries the
vendor's raw code and message (when there was one) for logging, but callers
should never need to branch on them.
"""

from __future__ import annotations


class ShippingError(Exception):
    """Base class for every error the facade raises."""

    def __init__(self, message: str, *, vendor_code: int | None = None) -> None:
        super().__init__(message)
        self.vendor_code = vendor_code


class ValidationError(ShippingError):
    """Input was rejected locally, before any vendor call was made."""


class AuthenticationError(ShippingError):
    """The configured account or key was refused."""


class InvalidShipmentError(ShippingError):
    """The vendor rejected the request contents (bad address, unknown service...)."""


class ShipmentNotFoundError(ShippingError):
    """No shipment exists for the given tracking number."""


class CancellationRejectedError(ShippingError):
    """The shipment can no longer be cancelled (already voided or in the network)."""


class ProviderUnavailableError(ShippingError):
    """The vendor stayed unavailable after every retry."""


class UnexpectedResponseError(ShippingError):
    """The vendor answered in a shape the facade could not interpret."""
