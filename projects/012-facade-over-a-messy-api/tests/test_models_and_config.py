from decimal import Decimal

import pytest

from shipping_facade import Address, Parcel, ShippingConfig, ValidationError


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"name": "  "}, "name"),
        ({"state": "Texas"}, "state"),
        ({"postal_code": "7520"}, "postal_code"),
        ({"country": "usa"}, "country"),
    ],
)
def test_address_rejects_bad_fields(overrides, message):
    fields = {"name": "A", "street1": "1 Main", "city": "Austin", "state": "TX", "postal_code": "78701"}
    with pytest.raises(ValidationError, match=message):
        Address(**(fields | overrides))


def test_parcel_coerces_numbers_to_decimal():
    parcel = Parcel(2, "1.5", 10, 10)
    assert parcel.weight_kg == Decimal("2") and isinstance(parcel.length_cm, Decimal)


@pytest.mark.parametrize("bad", [0, -1, "abc", "NaN"])
def test_parcel_rejects_non_positive_or_invalid(bad):
    with pytest.raises(ValidationError):
        Parcel(bad, 10, 10, 10)


def test_config_from_env():
    cfg = ShippingConfig.from_env(
        {"ACME_ACCOUNT": "acct", "ACME_API_KEY": "k", "ACME_ENV": "PROD", "ACME_MAX_ATTEMPTS": "5"}
    )
    assert (cfg.account, cfg.environment, cfg.max_attempts, cfg.backoff_seconds) == ("acct", "PROD", 5, 0.2)


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"ACME_ACCOUNT": "a", "ACME_API_KEY": "k", "ACME_ENV": "STAGING"},
        {"ACME_ACCOUNT": "a", "ACME_API_KEY": "k", "ACME_MAX_ATTEMPTS": "0"},
        {"ACME_ACCOUNT": "a", "ACME_API_KEY": "k", "ACME_MAX_ATTEMPTS": "three"},
    ],
)
def test_config_rejects_invalid_env(env):
    with pytest.raises(ValidationError):
        ShippingConfig.from_env(env)
