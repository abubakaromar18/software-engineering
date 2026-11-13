import json
from decimal import Decimal

import pytest

from rules_dsl import (
    ConfigError,
    EngineConfig,
    ErrorPolicy,
    InvalidRulesetError,
    RuleEngine,
    RuleError,
    RuleStatus,
    builtin_functions,
    parse,
)


def run(text: str, facts: dict | None = None, policy: ErrorPolicy = ErrorPolicy.RAISE):
    engine = RuleEngine(parse(text), config=EngineConfig(on_error=policy))
    return engine.evaluate(facts or {})


def statuses(outcome) -> dict[str, RuleStatus]:
    return {entry.rule: entry.status for entry in outcome.trace}


def test_rules_run_by_priority_and_see_earlier_results():
    outcome = run(
        """
        rule "second" priority 1 when result.base > 10 then set doubled = result.base * 2 end
        rule "first" priority 5 when true then set base = x end
        """,
        {"x": 21},
    )
    assert outcome.results == {"base": Decimal(21), "doubled": Decimal(42)}
    assert outcome.fired == ["first", "second"]


def test_compound_assignment_starts_from_zero_and_accumulates():
    outcome = run(
        """
        rule "a" priority 2 when true then set d += 5 end
        rule "b" priority 1 when true then set d += 2.50 set d -= 1 end
        """
    )
    assert outcome.results["d"] == Decimal("6.50")


def test_compound_assignment_on_a_string_fails():
    with pytest.raises(RuleError, match="'\\+=' needs numbers"):
        run('rule "a" when true then set s = "x" set s += 1 end')


def test_tags_are_ordered_and_deduplicated():
    outcome = run(
        """
        rule "a" priority 2 when true then tag "x" tag "y" tag "x" end
        rule "b" priority 1 when true then tag "y" tag "z" end
        """
    )
    assert outcome.tags == ["x", "y", "z"]


def test_stop_halts_lower_priority_rules():
    outcome = run(
        """
        rule "gate" priority 9 when blocked then set reason = "blocked" stop end
        rule "later" when true then set reached = true end
        """,
        {"blocked": True},
    )
    assert statuses(outcome) == {"gate": RuleStatus.FIRED, "later": RuleStatus.NOT_REACHED}
    assert "reached" not in outcome.results


def test_raise_policy_reports_the_rule_and_location():
    with pytest.raises(RuleError) as info:
        run('rule "bad one" when true then set x = 1 / zero end', {"zero": 0})
    assert info.value.rule == "bad one"
    assert "division by zero" in info.value.message
    assert info.value.span.line == 1


def test_skip_policy_rolls_back_the_failing_rule_entirely():
    outcome = run(
        """
        rule "partial" priority 2
        when true
        then
            set a = 1
            tag "half-done"
            set b = 1 / 0
        end
        rule "fine" priority 1 when true then set c = 3 end
        """,
        policy=ErrorPolicy.SKIP,
    )
    assert outcome.results == {"c": Decimal(3)}  # no "a": the rule was atomic
    assert outcome.tags == []
    entry = outcome.trace[0]
    assert entry.status is RuleStatus.FAILED and "division by zero" in entry.error.message


def test_conditions_must_be_boolean():
    with pytest.raises(RuleError, match="rule condition must be a boolean, got number 1"):
        run('rule "a" when x then stop end', {"x": 1})


def test_trace_records_each_change():
    outcome = run('rule "a" when true then set x = 1 set x = 2 end')
    assert [(c.name, c.value) for c in outcome.trace[0].changes] == [
        ("x", Decimal(1)),
        ("x", Decimal(2)),
    ]


def test_facts_from_json_floats_stay_exact():
    facts = json.loads('{"price": 0.1, "qty": 3}')
    outcome = run('rule "a" when true then set total = price * qty end', facts)
    assert outcome.results["total"] == Decimal("0.3")
    assert outcome.to_json() == {"results": {"total": "0.3"}, "tags": [], "fired": ["a"]}


def test_result_is_a_reserved_fact_name():
    with pytest.raises(ConfigError, match="reserved"):
        run('rule "a" when true then stop end', {"result": 1})


def test_facts_must_be_a_mapping_of_supported_values():
    engine = RuleEngine(parse('rule "a" when true then stop end'))
    with pytest.raises(ConfigError, match="must be an object"):
        engine.evaluate([1, 2])  # type: ignore[arg-type]
    with pytest.raises(ConfigError, match="unsupported fact value"):
        engine.evaluate({"when": object()})


def test_engine_is_reusable_across_evaluations():
    engine = RuleEngine(parse('rule "a" when x > 1 then set big = true end'))
    assert engine.evaluate({"x": 5}).results == {"big": True}
    assert engine.evaluate({"x": 0}).results == {}


def test_custom_functions_extend_the_language():
    functions = builtin_functions()

    @functions.register("vat", 2, 2, "price including VAT for a country")
    def vat(price, country):
        return price * {"DE": Decimal("1.19"), "FR": Decimal("1.20")}[country]

    engine = RuleEngine.from_source(
        'rule "gross" when true then set gross = vat(net, "DE") end', functions=functions
    )
    assert engine.evaluate({"net": 100}).results["gross"] == Decimal("119.00")
    failing = RuleEngine(parse('rule "g" when true then set g = vat(net, c) end'), functions)
    with pytest.raises(RuleError, match="vat\\(\\) failed: 'XX'"):
        failing.evaluate({"net": 1, "c": "XX"})


def test_registering_a_duplicate_function_is_refused():
    functions = builtin_functions()
    with pytest.raises(ConfigError, match="already registered"):
        functions.register("len", 1, 1)(lambda value: value)


def test_from_source_refuses_rulesets_with_checker_errors():
    with pytest.raises(InvalidRulesetError) as info:
        RuleEngine.from_source('rule "a" when true then set x = nope() end')
    assert "unknown function 'nope'" in info.value.render()


def test_checkout_example_end_to_end(examples):
    engine = RuleEngine.from_source((examples / "checkout.rules").read_text())
    order = json.loads((examples / "order.json").read_text())
    outcome = engine.evaluate(order)
    assert outcome.results == {
        "discount": Decimal("29.99"),
        "shipping": Decimal(0),
        "total": Decimal("119.91"),
    }
    assert outcome.tags == ["loyalty", "free-shipping"]

    order["order"]["country"] = "XX"
    blocked = engine.evaluate(order)
    assert blocked.results == {"discount": Decimal(0), "blocked": True}
    assert blocked.tags == ["compliance-hold"]

    newcomer = {
        "customer": {"tier": "basic", "orders": 0},
        "order": {"country": "US", "subtotal": 20, "items": ["mug"], "categories": ["home"]},
    }
    result = engine.evaluate(newcomer).results
    assert result == {
        "discount": Decimal(5),
        "shipping": Decimal("4.99"),
        "total": Decimal("19.99"),
    }
