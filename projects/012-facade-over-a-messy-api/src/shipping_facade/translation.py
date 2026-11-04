"""Pure functions that convert between the domain model and vendor payloads.

Keeping these free of I/O makes every unit conversion and parsing rule
testable on its own, and keeps the vendor's vocabulary in one file.
"""

from __future__ import annotations

import base64
from datetime import datetime
from decimal import ROUND_CEILING, Decimal

from shipping_facade.errors import UnexpectedResponseError
from shipping_facade.models import (
    Address,
    Money,
    Parcel,
    Quote,
    ServiceLevel,
    TrackingEvent,
    TrackingStatus,
)

LB_PER_KG = Decimal("2.20462262")
CM_PER_INCH = Decimal("2.54")
_TENTH = Decimal("0.1")

SERVICE_TO_VENDOR: dict[ServiceLevel, str] = {
    ServiceLevel.GROUND: "GND",
    ServiceLevel.TWO_DAY: "2DA",
    ServiceLevel.OVERNIGHT: "NDA",
}
VENDOR_TO_SERVICE = {code: level for level, code in SERVICE_TO_VENDOR.items()}

VENDOR_TO_STATUS: dict[str, TrackingStatus] = {
    "LC": TrackingStatus.LABEL_CREATED,
    "PU": TrackingStatus.PICKED_UP,
    "IT": TrackingStatus.IN_TRANSIT,
    "OD": TrackingStatus.OUT_FOR_DELIVERY,
    "DL": TrackingStatus.DELIVERED,
    "VD": TrackingStatus.CANCELLED,
}


# ------------------------------------------------------------ outbound
def to_vendor_address(address: Address) -> dict[str, str]:
    payload = {
        "nm": address.name,
        "a1": address.street1,
        "cty": address.city,
        "st": address.state,
        "zp": address.postal_code,
        "ctry": address.country,
    }
    if address.street2:
        payload["a2"] = address.street2
    return payload


def _round_up_tenth(value: Decimal) -> Decimal:
    # Round *up* so we never under-declare a parcel and get surcharged later.
    return value.quantize(_TENTH, rounding=ROUND_CEILING)


def to_vendor_package(parcel: Parcel) -> str:
    """Encode a parcel as the vendor's ``WT=..;L=..;W=..;H=..`` string (lb/in)."""
    pounds = _round_up_tenth(parcel.weight_kg * LB_PER_KG)
    dims = [_round_up_tenth(d / CM_PER_INCH) for d in (parcel.length_cm, parcel.width_cm, parcel.height_cm)]
    return f"WT={pounds};L={dims[0]};W={dims[1]};H={dims[2]}"


def to_vendor_request(origin: Address, destination: Address, parcel: Parcel) -> dict:
    return {
        "frm": to_vendor_address(origin),
        "to": to_vendor_address(destination),
        "pkg": to_vendor_package(parcel),
    }


# ------------------------------------------------------------- inbound
def cents_to_money(cents: str) -> Money:
    if not cents.isdigit():
        raise UnexpectedResponseError(f"expected a cents string, got {cents!r}")
    return Money(Decimal(cents) / 100)


def from_vendor_rates(rates: list[dict]) -> list[Quote]:
    """Map vendor rates to quotes, skipping services we do not offer."""
    quotes = []
    for rate in rates:
        level = VENDOR_TO_SERVICE.get(rate.get("svc", ""))
        if level is None:
            continue
        quotes.append(Quote(level, cents_to_money(rate["amt"]), int(rate["eta"])))
    return sorted(quotes, key=lambda q: q.price.amount)


def decode_label(encoded: str) -> bytes:
    try:
        return base64.b64decode(encoded, validate=True)
    except ValueError as exc:
        raise UnexpectedResponseError("label is not valid base64") from exc


def parse_track_envelope(raw: str) -> dict:
    """Turn ``'RC=0~body'`` into the ``{'rc': .., ...}`` shape other calls use."""
    head, sep, body = raw.partition("~")
    if not sep or not head.startswith("RC=") or not head[3:].isdigit():
        raise UnexpectedResponseError(f"unrecognised tracking response {raw[:40]!r}")
    rc = int(head[3:])
    return {"rc": rc, "body": body} if rc == 0 else {"rc": rc, "msg": body}


def parse_tracking_events(body: str) -> tuple[TrackingEvent, ...]:
    """Parse ``'YYYYMMDD HHMMSS|CODE|DESC;...'`` into typed events."""
    events = []
    for line in filter(None, body.split(";")):
        try:
            stamp, code, description = line.split("|", 2)
            timestamp = datetime.strptime(stamp, "%Y%m%d %H%M%S")
        except ValueError as exc:
            raise UnexpectedResponseError(f"malformed tracking line {line!r}") from exc
        status = VENDOR_TO_STATUS.get(code)
        if status is None:
            raise UnexpectedResponseError(f"unknown tracking code {code!r}")
        # Free text is passed through verbatim: re-casing would mangle place names.
        events.append(TrackingEvent(timestamp, status, description))
    if not events:
        raise UnexpectedResponseError("tracking history is empty")
    return tuple(events)
