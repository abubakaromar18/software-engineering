"""``ShippingService``: the one class application code uses to ship parcels.

Four intention-revealing methods replace the vendor's PascalCase, rc-coded,
imperial-unit surface. Each method is a short script: translate the domain
objects out, let the gateway make the call, translate the answer back.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from acme_ship_sdk import AcmeShipClient
from shipping_facade import translation
from shipping_facade.config import ShippingConfig
from shipping_facade.errors import UnexpectedResponseError, ValidationError
from shipping_facade.gateway import VendorGateway
from shipping_facade.models import (
    Address,
    Parcel,
    Quote,
    ServiceLevel,
    Shipment,
    TrackingInfo,
)

T = TypeVar("T")


class ShippingService:
    def __init__(self, gateway: VendorGateway) -> None:
        self._gateway = gateway

    @classmethod
    def create(
        cls,
        config: ShippingConfig,
        client: AcmeShipClient | None = None,
        *,
        sleep: Callable[[float], None] | None = None,
    ) -> ShippingService:
        """Wire up the default gateway; pass ``client``/``sleep`` to substitute them."""
        kwargs = {} if sleep is None else {"sleep": sleep}
        return cls(VendorGateway(client or AcmeShipClient(), config, **kwargs))

    def quote(self, origin: Address, destination: Address, parcel: Parcel) -> list[Quote]:
        """All available services for this parcel, cheapest first."""
        request = translation.to_vendor_request(origin, destination, parcel)
        response = self._gateway.call("quote", lambda c: c.GetRates(request))
        return self._translated(lambda: translation.from_vendor_rates(response["rates"]))

    def cheapest(
        self, origin: Address, destination: Address, parcel: Parcel, *, max_days: int | None = None
    ) -> Quote:
        """The cheapest quote, optionally limited to services arriving within ``max_days``."""
        quotes = self.quote(origin, destination, parcel)
        eligible = [q for q in quotes if max_days is None or q.estimated_days <= max_days]
        if not eligible:
            raise ValidationError(f"no service delivers within {max_days} day(s)")
        return eligible[0]

    def ship(self, origin: Address, destination: Address, parcel: Parcel, service: ServiceLevel) -> Shipment:
        """Buy a label. Returns the tracking number, price paid and label PDF."""
        request = translation.to_vendor_request(origin, destination, parcel)
        request["svc"] = translation.SERVICE_TO_VENDOR[service]
        response = self._gateway.call("ship", lambda c: c.CreateLabel(request))
        return self._translated(
            lambda: Shipment(
                tracking_number=response["trk"],
                service=service,
                price=translation.cents_to_money(response["chg"]),
                label_pdf=translation.decode_label(response["lbl"]),
            )
        )

    def track(self, tracking_number: str) -> TrackingInfo:
        """Full scan history for a shipment, oldest event first."""
        response = self._gateway.call(
            "track",
            lambda c: translation.parse_track_envelope(c.Track(tracking_number)),
        )
        events = self._translated(lambda: translation.parse_tracking_events(response["body"]))
        return TrackingInfo(tracking_number, events)

    def cancel(self, tracking_number: str) -> None:
        """Void a label. Raises ``CancellationRejectedError`` once the parcel has moved."""
        self._gateway.call("cancel", lambda c: c.VoidLabel(tracking_number))

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _translated(build: Callable[[], T]) -> T:
        """Turn a missing or mistyped field in a vendor response into a facade error."""
        try:
            return build()
        except (KeyError, TypeError, ValueError) as exc:
            raise UnexpectedResponseError(f"unexpected response from vendor: {exc!r}") from exc
