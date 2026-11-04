"""Typed domain model the rest of the application speaks.

These types know nothing about the vendor. They use metric units, ``Decimal``
money and enums, and they validate themselves on construction so an invalid
parcel or address can never reach the gateway.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from shipping_facade.errors import ValidationError

_STATE_RE = re.compile(r"^[A-Z]{2}$")
_ZIP_RE = re.compile(r"^\d{5}$")


class ServiceLevel(Enum):
    GROUND = "ground"
    TWO_DAY = "two_day"
    OVERNIGHT = "overnight"


class TrackingStatus(Enum):
    LABEL_CREATED = "label_created"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Address:
    name: str
    street1: str
    city: str
    state: str
    postal_code: str
    country: str = "US"
    street2: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("name", "street1", "city"):
            if not getattr(self, field_name).strip():
                raise ValidationError(f"address {field_name} must not be blank")
        if not _STATE_RE.match(self.state):
            raise ValidationError(f"state must be a two-letter code, got {self.state!r}")
        if not _ZIP_RE.match(self.postal_code):
            raise ValidationError(f"postal_code must be 5 digits, got {self.postal_code!r}")
        if len(self.country) != 2 or not self.country.isupper():
            raise ValidationError(f"country must be an ISO 3166 alpha-2 code, got {self.country!r}")


@dataclass(frozen=True, slots=True)
class Parcel:
    """A box, measured in kilograms and centimetres."""

    weight_kg: Decimal
    length_cm: Decimal
    width_cm: Decimal
    height_cm: Decimal

    def __post_init__(self) -> None:
        for field_name in ("weight_kg", "length_cm", "width_cm", "height_cm"):
            value = getattr(self, field_name)
            if not isinstance(value, Decimal):
                # Accept ints/strs for convenience but store a Decimal.
                try:
                    value = Decimal(str(value))
                except ArithmeticError as exc:
                    raise ValidationError(f"{field_name} is not a number: {value!r}") from exc
                object.__setattr__(self, field_name, value)
            if not value.is_finite() or value <= 0:
                raise ValidationError(f"{field_name} must be positive, got {value}")


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"


@dataclass(frozen=True, slots=True)
class Quote:
    service: ServiceLevel
    price: Money
    estimated_days: int


@dataclass(frozen=True, slots=True)
class Shipment:
    tracking_number: str
    service: ServiceLevel
    price: Money
    label_pdf: bytes


@dataclass(frozen=True, slots=True)
class TrackingEvent:
    timestamp: datetime
    status: TrackingStatus
    description: str


@dataclass(frozen=True, slots=True)
class TrackingInfo:
    tracking_number: str
    events: tuple[TrackingEvent, ...]

    @property
    def status(self) -> TrackingStatus:
        return self.events[-1].status

    @property
    def is_delivered(self) -> bool:
        return self.status is TrackingStatus.DELIVERED
