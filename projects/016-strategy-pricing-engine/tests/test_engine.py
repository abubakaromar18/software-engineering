from datetime import date
from decimal import Decimal

import pytest
from conftest import D, cart, item
from hypothesis import given
from hypothesis import strategies as st

from pricing_engine.discounts import BuyXGetYFree, FixedAmountOff, PercentageOff
from pricing_engine.engine import PricingEngine
from pricing_engine.errors import NoTaxRuleError, StrategyError
from pricing_engine.models import Cart, LineItem
from pricing_engine.rules import Rule, always, negate, tier_in
from pricing_engine.stacking import BestForCustomer
from pricing_engine.taxes import FlatRateTax, NoTax

NO_TAX = [Rule("exempt", always, NoTax())]


def test_sequential_discounts_compound_in_priority_order():
    engine = PricingEngine(
        [
            Rule("second", always, FixedAmountOff(D("10.00")), priority=20),
            Rule("first", always, PercentageOff(D("50")), priority=10),
        ],
        NO_TAX,
    )
    quote = engine.quote(cart(item(price="100.00")))
    assert [(a.rule, a.amount) for a in quote.discounts] == [
        ("first", D("50.00")),
        ("second", D("10.00")),
    ]
    assert quote.total == D("40.00")


def test_best_for_customer_applies_only_the_largest():
    engine = PricingEngine(
        [
            Rule("small", always, PercentageOff(D("5"))),
            Rule("big", always, PercentageOff(D("20"))),
        ],
        NO_TAX,
        BestForCustomer(),
    )
    quote = engine.quote(cart(item(price="100.00")))
    assert [a.rule for a in quote.discounts] == ["big"]
    assert quote.total == D("80.00")


def test_best_for_customer_tie_goes_to_higher_priority():
    engine = PricingEngine(
        [
            Rule("later", always, FixedAmountOff(D("5.00")), priority=2),
            Rule("earlier", always, PercentageOff(D("5")), priority=1),
        ],
        NO_TAX,
        BestForCustomer(),
    )
    assert engine.quote(cart(item(price="100.00"))).discounts[0].rule == "earlier"


def test_ineligible_and_zero_rules_are_left_off_the_quote():
    engine = PricingEngine(
        [
            Rule("gold only", tier_in("gold"), PercentageOff(D("10"))),
            Rule("no effect", always, BuyXGetYFree(5, 1)),
        ],
        NO_TAX,
    )
    assert engine.quote(cart()).discounts == ()


def test_tax_is_charged_on_discounted_price():
    engine = PricingEngine(
        [Rule("half", always, PercentageOff(D("50")))],
        [Rule("vat", always, FlatRateTax(D("20")))],
    )
    quote = engine.quote(cart(item(price="100.00")))
    assert quote.tax_total == D("10.00")
    assert quote.total == D("60.00")


def test_first_matching_tax_rule_wins():
    engine = PricingEngine(
        [],
        [
            Rule("fallback", always, FlatRateTax(D("10")), priority=99),
            Rule("gold exempt", tier_in("gold"), NoTax(), priority=1),
        ],
    )
    assert engine.quote(cart(customer_tier="gold")).tax_rule == "gold exempt"
    assert engine.quote(cart()).tax_rule == "fallback"


def test_no_matching_tax_rule_fails_closed():
    engine = PricingEngine([], [Rule("never", negate(always), NoTax())])
    with pytest.raises(NoTaxRuleError):
        engine.quote(cart())


class _Stub:
    def __init__(self, amounts):
        self.amounts = amounts

    def discount(self, _lines):
        return self.amounts

    def tax(self, _lines):
        return self.amounts


def test_over_discount_is_capped_at_line_value():
    engine = PricingEngine([Rule("huge", always, _Stub([D("999.00")]))], NO_TAX)
    quote = engine.quote(cart(item(price="10.00")))
    assert quote.total == D("0.00")
    assert quote.discounts[0].amount == D("10.00")


@pytest.mark.parametrize("amounts", [[D("-1.00")], [D("1.00"), D("1.00")], []])
def test_misbehaving_discount_strategy_is_rejected(amounts):
    engine = PricingEngine([Rule("bad", always, _Stub(amounts))], NO_TAX)
    with pytest.raises(StrategyError, match="bad"):
        engine.quote(cart())


@pytest.mark.parametrize("amounts", [[D("-1.00")], []])
def test_misbehaving_tax_strategy_is_rejected(amounts):
    engine = PricingEngine([], [Rule("bad", always, _Stub(amounts))])
    with pytest.raises(StrategyError, match="bad"):
        engine.quote(cart())


line_items = st.builds(
    lambda price, qty, cat: (Decimal(price) / 100, qty, cat),
    st.integers(0, 100_000),
    st.integers(1, 100),
    st.sampled_from(["a", "b"]),
)
discount_strategies = st.one_of(
    st.integers(0, 100).map(lambda p: PercentageOff(Decimal(p))),
    st.integers(0, 500_000).map(lambda c: FixedAmountOff(Decimal(c) / 100)),
    st.tuples(st.integers(1, 4), st.integers(1, 4)).map(lambda t: BuyXGetYFree(*t)),
)


@given(st.lists(line_items, min_size=1, max_size=8), st.lists(discount_strategies, max_size=5))
def test_quote_invariants(raw_items, strategies):
    items = tuple(LineItem(f"S{i}", c, p, q) for i, (p, q, c) in enumerate(raw_items))
    rules = [Rule(f"r{i}", always, s) for i, s in enumerate(strategies)]
    engine = PricingEngine(rules, [Rule("vat", always, FlatRateTax(D("20")))])
    quote = engine.quote(Cart(items=items, order_date=date(2026, 1, 1)))

    assert all(line.net >= 0 and line.tax >= 0 for line in quote.lines)
    assert all(line.net + line.discount == line.gross for line in quote.lines)
    assert sum(a.amount for a in quote.discounts) == quote.discount_total
    assert quote.total == sum(line.total for line in quote.lines)
