import pytest
from conftest import D, item, priced

from pricing_engine.discounts import (
    BuyXGetYFree,
    CategoryScoped,
    FixedAmountOff,
    PercentageOff,
    VolumeTiers,
)
from pricing_engine.errors import ConfigError, StrategyError
from pricing_engine.taxes import CategoryRateTax, FlatRateTax, NoTax


def test_percentage_rounds_each_line():
    lines = priced(item("A", price="9.99"), item("B", price="0.05"))
    assert PercentageOff(D("10")).discount(lines) == [D("1.00"), D("0.01")]


def test_fixed_amount_is_spread_by_net_value():
    lines = priced(item("A", price="30.00"), item("B", price="10.00"))
    assert FixedAmountOff(D("4.00")).discount(lines) == [D("3.00"), D("1.00")]


def test_fixed_amount_never_exceeds_order_value():
    assert FixedAmountOff(D("50.00")).discount(priced(item(price="10.00"))) == [D("10.00")]


@pytest.mark.parametrize(
    ("quantity", "expected"), [(2, "0.00"), (3, "10.00"), (5, "10.00"), (6, "20.00")]
)
def test_buy_two_get_one(quantity, expected):
    lines = priced(item(price="10.00", quantity=quantity))
    assert BuyXGetYFree(2, 1).discount(lines) == [D(expected)]


@pytest.mark.parametrize(
    ("quantity", "expected"), [(9, "0.00"), (10, "0.50"), (49, "2.45"), (50, "7.50")]
)
def test_volume_uses_highest_tier_reached(quantity, expected):
    tiers = VolumeTiers(((10, D("5")), (50, D("15"))))
    assert tiers.discount(priced(item(price="1.00", quantity=quantity))) == [D(expected)]


def test_scope_limits_lines_and_fixed_allocation():
    lines = priced(item("A", "books", "10.00"), item("B", "toys", "90.00"))
    strategy = CategoryScoped(FixedAmountOff(D("5.00")), frozenset({"books"}))
    assert strategy.discount(lines) == [D("5.00"), D("0.00")]


def test_scope_rejects_inner_strategy_returning_wrong_length():
    class Broken:
        def discount(self, _lines):
            return [D("1.00"), D("1.00")]

    lines = priced(item("A", "books"), item("B", "toys"))
    with pytest.raises(StrategyError):
        CategoryScoped(Broken(), frozenset({"books"})).discount(lines)


@pytest.mark.parametrize(
    "build",
    [
        lambda: PercentageOff(D("101")),
        lambda: PercentageOff(D("-1")),
        lambda: FixedAmountOff(D("-1.00")),
        lambda: FixedAmountOff(D("0.001")),
        lambda: BuyXGetYFree(0, 1),
        lambda: VolumeTiers(()),
        lambda: VolumeTiers(((0, D("5")),)),
        lambda: FlatRateTax(D("-1")),
        lambda: CategoryRateTax(D("5"), {"food": D("-2")}),
    ],
)
def test_invalid_parameters_are_rejected(build):
    with pytest.raises(ConfigError):
        build()


def test_taxes():
    lines = priced(item("A", "food", "10.00"), item("B", "toys", "10.00"))
    assert NoTax().tax(lines) == [D("0.00"), D("0.00")]
    assert FlatRateTax(D("7.25")).tax(lines) == [D("0.73"), D("0.73")]
    assert CategoryRateTax(D("20"), {"food": D("0")}).tax(lines) == [D("0.00"), D("2.00")]
