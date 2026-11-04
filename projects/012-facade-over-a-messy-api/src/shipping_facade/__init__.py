"""A clean, typed facade over the AcmeShip legacy SDK.

Import everything an application needs from here; the submodules are
implementation detail.
"""

from shipping_facade.config import ShippingConfig
from shipping_facade.errors import (
    AuthenticationError,
    CancellationRejectedError,
    InvalidShipmentError,
    ProviderUnavailableError,
    ShipmentNotFoundError,
    ShippingError,
    UnexpectedResponseError,
    ValidationError,
)
from shipping_facade.facade import ShippingService
from shipping_facade.models import (
    Address,
    Money,
    Parcel,
    Quote,
    ServiceLevel,
    Shipment,
    TrackingEvent,
    TrackingInfo,
    TrackingStatus,
)

__all__ = [
    "Address",
    "AuthenticationError",
    "CancellationRejectedError",
    "InvalidShipmentError",
    "Money",
    "Parcel",
    "ProviderUnavailableError",
    "Quote",
    "ServiceLevel",
    "Shipment",
    "ShipmentNotFoundError",
    "ShippingConfig",
    "ShippingError",
    "ShippingService",
    "TrackingEvent",
    "TrackingInfo",
    "TrackingStatus",
    "UnexpectedResponseError",
    "ValidationError",
]
