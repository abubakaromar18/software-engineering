import base64
from datetime import datetime
from decimal import Decimal

import pytest

from shipping_facade import Address, Parcel, ServiceLevel, TrackingStatus, UnexpectedResponseError
from shipping_facade import translation as t


def test_package_string_converts_to_imperial_and_rounds_up():
    # 1 kg = 2.2046 lb -> 2.3; 10 cm = 3.937 in -> 4.0; 2.54 cm is exactly 1.0 in.
    assert t.to_vendor_package(Parcel(1, 10, Decimal("2.54"), 5)) == "WT=2.3;L=4.0;W=1.0;H=2.0"


def test_address_uses_vendor_keys_and_omits_empty_street2():
    addr = Address("Ada", "12 Way", "Brooklyn", "NY", "11201")
    assert t.to_vendor_address(addr) == {
        "nm": "Ada",
        "a1": "12 Way",
        "cty": "Brooklyn",
        "st": "NY",
        "zp": "11201",
        "ctry": "US",
    }
    assert t.to_vendor_address(Address("Ada", "12 Way", "B", "NY", "11201", street2="Apt 3"))["a2"] == "Apt 3"


def test_rates_become_sorted_quotes_and_unknown_services_are_skipped():
    quotes = t.from_vendor_rates(
        [
            {"svc": "NDA", "amt": "3499", "eta": "1"},
            {"svc": "XYZ", "amt": "1", "eta": "9"},
            {"svc": "GND", "amt": "899", "eta": "5"},
        ]
    )
    assert [q.service for q in quotes] == [ServiceLevel.GROUND, ServiceLevel.OVERNIGHT]
    assert quotes[0].price.amount == Decimal("8.99") and quotes[0].estimated_days == 5


@pytest.mark.parametrize("bad", ["12.99", "-5", ""])
def test_cents_must_be_digits(bad):
    with pytest.raises(UnexpectedResponseError):
        t.cents_to_money(bad)


def test_track_envelope_success_and_error():
    assert t.parse_track_envelope("RC=0~x|y") == {"rc": 0, "body": "x|y"}
    assert t.parse_track_envelope("RC=404~NO SUCH TRK") == {"rc": 404, "msg": "NO SUCH TRK"}
    with pytest.raises(UnexpectedResponseError):
        t.parse_track_envelope("<html>502 Bad Gateway</html>")


def test_tracking_events_are_parsed_in_order():
    events = t.parse_tracking_events("20260105 090000|LC|LABEL CREATED;20260105 150000|PU|SCANNED AT HUB")
    assert [e.status for e in events] == [TrackingStatus.LABEL_CREATED, TrackingStatus.PICKED_UP]
    assert events[1].timestamp == datetime(2026, 1, 5, 15, 0) and events[1].description == "SCANNED AT HUB"


@pytest.mark.parametrize("body", ["", "garbage", "20260105 090000|ZZ|WHAT", "2026-01-05|LC|X"])
def test_malformed_tracking_raises(body):
    with pytest.raises(UnexpectedResponseError):
        t.parse_tracking_events(body)


def test_label_decoding():
    assert t.decode_label(base64.b64encode(b"%PDF").decode()) == b"%PDF"
    with pytest.raises(UnexpectedResponseError):
        t.decode_label("not base64!!")


def test_every_service_level_has_a_vendor_code():
    assert set(t.SERVICE_TO_VENDOR) == set(ServiceLevel)
