from datetime import date

from conftest import D, cart, item

from pricing_engine import rules as r


def test_leaf_conditions():
    c = cart(item(price="50.00"), region="DE", customer_tier="gold", coupons=frozenset({"X"}))
    assert r.tier_in("gold", "silver")(c)
    assert not r.tier_in("silver")(c)
    assert r.region_in("DE")(c)
    assert r.has_coupon("x")(c)
    assert r.min_subtotal(D("50.00"))(c)
    assert not r.min_subtotal(D("50.01"))(c)


def test_date_window_is_inclusive():
    window = r.date_between(date(2026, 6, 15), date(2026, 6, 16))
    assert window(cart(order_date=date(2026, 6, 15)))
    assert window(cart(order_date=date(2026, 6, 16)))
    assert not window(cart(order_date=date(2026, 6, 17)))


def test_combinators():
    c = cart()
    never = r.negate(r.always)
    assert r.all_of(r.always, r.always)(c)
    assert not r.all_of(r.always, never)(c)
    assert r.any_of(never, r.always)(c)
    assert not r.any_of(never, never)(c)
