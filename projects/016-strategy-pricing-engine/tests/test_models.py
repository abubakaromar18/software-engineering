from datetime import date
from decimal import Decimal

import pytest
from conftest import D, cart, item
from hypothesis import given
from hypothesis import strategies as st

from pricing_engine.errors import InvalidCartError
from pricing_engine.models import Cart, LineItem, allocate_pro_rata, percent_of, to_cents


def test_rounding_is_half_up():
    assert to_cents(D("1.005")) == D("1.01")
    assert percent_of(D("0.50"), D("1")) == D("0.01")


def test_allocation_preserves_total_and_breaks_ties_towards_earliest():
    assert allocate_pro_rata(D("10.00"), [D("1.00")] * 3) == [D("3.34"), D("3.33"), D("3.33")]


def test_allocation_with_zero_weights_is_zero():
    assert allocate_pro_rata(D("5.00"), [D("0.00"), D("0.00")]) == [D("0.00"), D("0.00")]


cents = st.integers(min_value=0, max_value=10_000_000).map(lambda c: Decimal(c) / 100)


@given(cents, st.lists(cents, min_size=1, max_size=20))
def test_allocation_always_sums_exactly(amount, weights):
    parts = allocate_pro_rata(amount, weights)
    if sum(weights) == 0:
        assert sum(parts) == 0
    else:
        assert sum(parts) == amount


@pytest.mark.parametrize(
    "kwargs",
    [
        {"sku": ""},
        {"category": ["x"]},
        {"unit_price": D("-1.00")},
        {"unit_price": D("1.005")},
        {"unit_price": D("NaN")},
        {"unit_price": 1.5},
        {"quantity": 0},
        {"quantity": True},
    ],
)
def test_invalid_line_items_are_rejected(kwargs):
    values = {"sku": "A", "category": "c", "unit_price": D("1.00"), "quantity": 1} | kwargs
    with pytest.raises(InvalidCartError):
        LineItem(**values)


def test_cart_rejects_duplicates_and_empty():
    with pytest.raises(InvalidCartError):
        cart(item("A"), item("A"))
    with pytest.raises(InvalidCartError):
        Cart(items=(), order_date=date(2026, 1, 1))


def test_coupons_are_case_insensitive():
    assert cart(coupons=frozenset({"save10"})).has_coupon("SAVE10")
