"""End-to-end walkthrough against the simulated vendor: ``python -m shipping_facade.demo``.

The vendor is configured to be flaky and to expire sessions quickly, so the
log lines show the gateway absorbing both problems while the calling code
below stays oblivious.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from acme_ship_sdk import AcmeShipClient
from shipping_facade import (
    Address,
    CancellationRejectedError,
    Parcel,
    ServiceLevel,
    ShippingConfig,
    ShippingService,
)

WAREHOUSE = Address("Acme Warehouse", "100 Commerce St", "Dallas", "TX", "75201")
CUSTOMER = Address("Ada Lovelace", "12 Analytical Way", "Brooklyn", "NY", "11201", street2="Apt 3")
BOX = Parcel(Decimal("2.5"), Decimal("30"), Decimal("20"), Decimal("15"))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="  [%(levelname)s] %(message)s")
    # The sandbox credentials are the simulator's built-in test account.
    config = ShippingConfig(account="ACME-TEST-001", api_key="sandbox-key", backoff_seconds=0.01)
    vendor = AcmeShipClient(flaky_every=4, session_ttl_calls=3)
    service = ShippingService.create(config, vendor)

    print("Quotes for a 2.5 kg box, Dallas -> Brooklyn:")
    for quote in service.quote(WAREHOUSE, CUSTOMER, BOX):
        print(f"  {quote.service.value:<10} {quote.price}  ~{quote.estimated_days} day(s)")

    best = service.cheapest(WAREHOUSE, CUSTOMER, BOX, max_days=2)
    print(f"\nCheapest within 2 days: {best.service.value} at {best.price}")

    shipment = service.ship(WAREHOUSE, CUSTOMER, BOX, ServiceLevel.TWO_DAY)
    print(f"Shipped: {shipment.tracking_number} ({len(shipment.label_pdf)}-byte label)")

    for _ in range(2):
        vendor._simulate_scan(shipment.tracking_number)  # the carrier moves the parcel
    info = service.track(shipment.tracking_number)
    print(f"\nTracking {info.tracking_number}: {info.status.value}")
    for event in info.events:
        print(f"  {event.timestamp:%Y-%m-%d %H:%M}  {event.status.value:<16} {event.description}")

    try:
        service.cancel(shipment.tracking_number)
    except CancellationRejectedError as exc:
        print(f"\nCancel refused: {exc}")


if __name__ == "__main__":
    main()
