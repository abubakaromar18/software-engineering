"""Behaviour of ShippingService against the simulated vendor SDK."""

from dataclasses import replace

import pytest

from acme_ship_sdk import AcmeShipClient
from shipping_facade import (
    Address,
    AuthenticationError,
    CancellationRejectedError,
    InvalidShipmentError,
    ProviderUnavailableError,
    ServiceLevel,
    ShipmentNotFoundError,
    TrackingStatus,
    UnexpectedResponseError,
    ValidationError,
)


# --------------------------------------------------------------- happy path
def test_quote_returns_all_services_cheapest_first(make_service, origin, destination, parcel):
    service, _ = make_service()
    quotes = service.quote(origin, destination, parcel)
    assert [q.service for q in quotes] == [ServiceLevel.GROUND, ServiceLevel.TWO_DAY, ServiceLevel.OVERNIGHT]
    assert all(a.price.amount < b.price.amount for a, b in zip(quotes, quotes[1:], strict=False))


def test_cheapest_respects_delivery_deadline(make_service, origin, destination, parcel):
    service, _ = make_service()
    assert service.cheapest(origin, destination, parcel).service is ServiceLevel.GROUND
    assert service.cheapest(origin, destination, parcel, max_days=2).service is ServiceLevel.TWO_DAY
    with pytest.raises(ValidationError):
        service.cheapest(origin, destination, parcel, max_days=0)


def test_ship_charges_the_quoted_price(make_service, origin, destination, parcel):
    service, _ = make_service()
    quoted = {q.service: q.price for q in service.quote(origin, destination, parcel)}
    shipment = service.ship(origin, destination, parcel, ServiceLevel.OVERNIGHT)
    assert shipment.price == quoted[ServiceLevel.OVERNIGHT]
    assert shipment.tracking_number.startswith("1Z")
    assert shipment.label_pdf.startswith(b"%PDF")


def test_track_follows_the_parcel_to_delivery(make_service, origin, destination, parcel):
    service, vendor = make_service()
    trk = service.ship(origin, destination, parcel, ServiceLevel.GROUND).tracking_number
    assert service.track(trk).status is TrackingStatus.LABEL_CREATED
    for _ in range(4):
        vendor._simulate_scan(trk)
    info = service.track(trk)
    assert info.is_delivered
    assert [e.status for e in info.events] == [
        TrackingStatus.LABEL_CREATED,
        TrackingStatus.PICKED_UP,
        TrackingStatus.IN_TRANSIT,
        TrackingStatus.OUT_FOR_DELIVERY,
        TrackingStatus.DELIVERED,
    ]
    assert "BROOKLYN NY" in info.events[-1].description


def test_cancel_before_pickup_then_cannot_cancel_twice(make_service, origin, destination, parcel):
    service, _ = make_service()
    trk = service.ship(origin, destination, parcel, ServiceLevel.GROUND).tracking_number
    service.cancel(trk)
    assert service.track(trk).status is TrackingStatus.CANCELLED
    with pytest.raises(CancellationRejectedError, match="Already void"):
        service.cancel(trk)


def test_cancel_after_pickup_is_rejected(make_service, origin, destination, parcel):
    service, vendor = make_service()
    trk = service.ship(origin, destination, parcel, ServiceLevel.GROUND).tracking_number
    vendor._simulate_scan(trk)
    with pytest.raises(CancellationRejectedError) as excinfo:
        service.cancel(trk)
    assert excinfo.value.vendor_code == 409


# ------------------------------------------------------------ error mapping
def test_unknown_tracking_number(make_service):
    service, _ = make_service()
    with pytest.raises(ShipmentNotFoundError):
        service.track("1ZNOPE")
    with pytest.raises(ShipmentNotFoundError):
        service.cancel("1ZNOPE")


def test_vendor_rejection_becomes_invalid_shipment(make_service, origin, parcel):
    service, _ = make_service()
    abroad = Address("Hans", "1 Strasse", "Berlin", "BE", "10115", country="DE")
    with pytest.raises(InvalidShipmentError, match="Domestic only"):
        service.quote(origin, abroad, parcel)


def test_bad_credentials(make_service, config, origin, destination, parcel):
    service, _ = make_service(cfg=replace(config, api_key="wrong"))
    with pytest.raises(AuthenticationError):
        service.quote(origin, destination, parcel)


def test_malformed_vendor_payload_is_wrapped(make_service, origin, destination, parcel, monkeypatch):
    service, vendor = make_service()
    monkeypatch.setattr(vendor, "GetRates", lambda payload: {"rc": 0})  # 'rates' missing
    with pytest.raises(UnexpectedResponseError):
        service.quote(origin, destination, parcel)


# --------------------------------------------------------------- resilience
def test_transient_busy_is_retried(make_service, sleeps, origin, destination, parcel):
    # Every second vendor request is busy, so the second quote needs one retry.
    service, _ = make_service(AcmeShipClient(flaky_every=2))
    service.quote(origin, destination, parcel)  # request 1 succeeds
    service.quote(origin, destination, parcel)  # request 2 busy, 3 succeeds
    assert sleeps == [0.5]


def test_gives_up_after_max_attempts(make_service, config, sleeps, origin, destination, parcel):
    service, _ = make_service(AcmeShipClient(flaky_every=1), cfg=replace(config, max_attempts=3))
    with pytest.raises(ProviderUnavailableError, match="3 attempts"):
        service.quote(origin, destination, parcel)
    assert sleeps == [0.5, 1.0]  # no pointless sleep after the final attempt


def test_expired_session_reconnects_transparently(make_service, sleeps, origin, destination, parcel):
    service, vendor = make_service(AcmeShipClient(session_ttl_calls=2))
    for _ in range(5):
        service.quote(origin, destination, parcel)
    assert vendor.connect_count == 3  # initial connect + reconnect after calls 2 and 4
    assert sleeps == []  # reconnecting is not a retry


def test_connects_lazily_and_only_once(make_service, origin, destination, parcel):
    service, vendor = make_service()
    assert vendor.connect_count == 0
    service.quote(origin, destination, parcel)
    service.quote(origin, destination, parcel)
    assert vendor.connect_count == 1
