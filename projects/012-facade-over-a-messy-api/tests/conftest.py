from decimal import Decimal

import pytest

from acme_ship_sdk import AcmeShipClient
from shipping_facade import Address, Parcel, ShippingConfig, ShippingService


@pytest.fixture
def origin() -> Address:
    return Address("Acme Warehouse", "100 Commerce St", "Dallas", "TX", "75201")


@pytest.fixture
def destination() -> Address:
    return Address("Ada Lovelace", "12 Analytical Way", "Brooklyn", "NY", "11201")


@pytest.fixture
def parcel() -> Parcel:
    return Parcel(Decimal("2.5"), Decimal("30"), Decimal("20"), Decimal("15"))


@pytest.fixture
def config() -> ShippingConfig:
    return ShippingConfig(account="ACME-TEST-001", api_key="sandbox-key", backoff_seconds=0.5)


@pytest.fixture
def sleeps() -> list[float]:
    """Records backoff delays instead of sleeping."""
    return []


@pytest.fixture
def make_service(config, sleeps):
    def factory(client: AcmeShipClient | None = None, cfg: ShippingConfig | None = None):
        vendor = client or AcmeShipClient()
        return ShippingService.create(cfg or config, vendor, sleep=sleeps.append), vendor

    return factory
