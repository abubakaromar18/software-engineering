import json
from decimal import Decimal
from pathlib import Path

import pytest
from conftest import D, cart

from pricing_engine import StrategyRegistry, cart_from_dict, engine_from_config
from pricing_engine.cli import main
from pricing_engine.errors import ConfigError, InvalidCartError
from pricing_engine.loader import default_discount_registry, parse_condition

EXAMPLES = Path(__file__).parent.parent / "examples"
TAX = [{"name": "t", "strategy": {"type": "none"}}]


def config(strategy=None, **rule):
    rule = {"name": "d", "strategy": strategy or {"type": "percentage", "percent": "10"}} | rule
    return {"discounts": [rule], "taxes": TAX}


def test_end_to_end_from_config():
    engine = engine_from_config(config(when={"tier": "gold"}))
    assert engine.quote(cart(customer_tier="gold")).total == D("9.00")
    assert engine.quote(cart()).total == D("10.00")


def test_nested_conditions():
    condition = parse_condition({"all": [{"any": [{"tier": "gold"}]}, {"not": {"region": "DE"}}]})
    assert condition(cart(customer_tier="gold", region="US"))
    assert not condition(cart(customer_tier="gold", region="DE"))


def test_categories_work_on_any_discount_type():
    spec = {"type": "fixed", "amount": "1.00", "categories": "other"}
    assert engine_from_config(config(spec)).quote(cart()).total == D("10.00")


def test_new_strategy_needs_no_engine_change():
    class HalfOff:
        def discount(self, lines):
            return [line.net / 2 for line in lines]

    registry: StrategyRegistry = default_discount_registry()
    registry.register("half", HalfOff)
    engine = engine_from_config(config({"type": "half"}), discount_registry=registry)
    assert engine.quote(cart()).total == D("5.00")


def test_duplicate_registration_is_rejected():
    with pytest.raises(ConfigError):
        default_discount_registry().register("percentage", object)


@pytest.mark.parametrize(
    "bad",
    [
        {"taxes": TAX, "typo": 1},
        {"discounts": []},
        {"taxes": TAX, "stacking": "nope"},
        config({"type": "nope"}),
        config({"type": "percentage"}),
        config({"type": "percentage", "percent": "10", "categoris": ["a"]}),
        config({"type": "percentage", "percent": 10.5}),
        config({"type": "percentage", "percent": "abc"}),
        config({"type": "percentage", "percent": "Infinity"}),
        config({"type": "volume", "tiers": [{"percent": "1"}]}),
        config(when={"unknown": 1}),
        config(when={"tier": "a", "region": "b"}),
        config(when={"between": ["2026-02-01", "2026-01-01"]}),
        config(when={"between": ["not-a-date", "2026-01-01"]}),
        config(priority="high"),
        config(extra=True),
        {"taxes": TAX * 2},
        {"taxes": 5},
    ],
)
def test_invalid_config_is_rejected(bad):
    with pytest.raises(ConfigError):
        engine_from_config(bad)


def test_cart_parsing_errors():
    good = {"order_date": "2026-01-01", "items": [
        {"sku": "A", "category": "c", "unit_price": "1.00", "quantity": 1}
    ]}
    assert cart_from_dict(good).subtotal == D("1.00")
    with pytest.raises(ConfigError):
        cart_from_dict(good | {"typo": 1})
    with pytest.raises(ConfigError):
        cart_from_dict(good | {"items": 5})
    with pytest.raises(InvalidCartError):
        cart_from_dict(good | {"items": []})


def test_cli_example_matches_hand_calculation(capsys):
    assert main(["--rules", str(EXAMPLES / "rules.json"),
                 "--cart", str(EXAMPLES / "cart.json"), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    # Bulk 13.50 + bundle 45.00 + gold 10% of 179.49 (per line: 17.95) + coupon 15.00.
    assert Decimal(output["subtotal"]) == D("237.99")
    assert Decimal(output["discount_total"]) == D("91.45")
    assert output["tax_rule"] == "Texas sales tax"
    assert [d["rule"] for d in output["discounts"]] == [
        "Bulk pens", "Book bundle 3-for-2", "Gold members 10% off", "Black Friday coupon",
    ]


def test_cli_prints_receipt(capsys):
    main(["--rules", str(EXAMPLES / "rules.json"), "--cart", str(EXAMPLES / "cart.json")])
    out = capsys.readouterr().out
    assert "Black Friday coupon" in out and "Total" in out


def test_cli_accepts_json_numbers_exactly(tmp_path, capsys):
    rules = tmp_path / "r.json"
    rules.write_text(json.dumps({"taxes": TAX}))
    basket = tmp_path / "c.json"
    basket.write_text('{"order_date": "2026-01-01", "items": '
                      '[{"sku": "A", "category": "c", "unit_price": 19.99, "quantity": 1}]}')
    assert main(["--rules", str(rules), "--cart", str(basket)]) == 0
    assert "19.99" in capsys.readouterr().out


def test_cli_reports_errors(tmp_path, capsys):
    assert main(["--rules", str(tmp_path / "missing"), "--cart", str(tmp_path / "x")]) == 2
    assert "error:" in capsys.readouterr().err
