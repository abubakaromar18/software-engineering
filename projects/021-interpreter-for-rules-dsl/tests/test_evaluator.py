from decimal import Decimal

import pytest
from helpers import evaluate

from rules_dsl import EvalError


def test_decimal_arithmetic_is_exact():
    assert evaluate("0.1 + 0.2") == Decimal("0.3")
    assert evaluate("order.total * 15%", {"order": {"total": 19.99}}) == Decimal("2.9985")


def test_string_concatenation():
    assert evaluate('"ab" + "cd"') == "abcd"


@pytest.mark.parametrize(
    ("expr", "message"),
    [
        ('"a" - 1', "needs two numbers"),
        ('"a" + 1', "two numbers or two strings"),
        ("1 / 0", "division by zero"),
        ('-"a"', "cannot negate a string"),
        ('1 < "2"', "cannot compare number < string"),
        ("1 and true", "must be a boolean"),
        ("not 1", "operand of 'not' must be a boolean"),
        ("1 in 2", "needs a list or string"),
        ('1 in "abc"', "needs a string on the left"),
        ("missing.fact", "unknown fact 'missing.fact'"),
        ("nope(1)", "unknown function"),
        ("len(1, 2)", "takes 1 argument"),
    ],
)
def test_runtime_errors_are_descriptive(expr, message):
    with pytest.raises(EvalError, match=message) as info:
        evaluate(expr)
    assert info.value.span is not None


def test_short_circuit_skips_the_right_operand():
    assert evaluate("false and 1 / 0 == 1") is False
    assert evaluate("true or missing.fact") is True


def test_equality_never_coerces_types():
    assert evaluate("true == 1") is False
    assert evaluate('1 == "1"') is False
    assert evaluate("1 == 1.00") is True
    assert evaluate("[1, true] == [1, true]") is True
    assert evaluate("[1] != [true]") is True


def test_membership_in_lists_and_strings():
    facts = {"c": {"tier": "gold"}}
    assert evaluate('c.tier in ["gold", "platinum"]', facts) is True
    assert evaluate('c.tier not in ["gold"]', facts) is False
    assert evaluate('"ol" in c.tier', facts) is True
    assert evaluate("true in [1]") is False  # no bool/number coercion here either


def test_ordering_on_strings():
    assert evaluate('"apple" < "banana"') is True


def test_has_tests_presence_without_failing():
    facts = {"customer": {"referral": None}}
    assert evaluate("has(customer.referral)", facts) is True  # present, even if null
    assert evaluate("has(customer.missing)", facts) is False
    assert evaluate("has(nobody.here)", facts) is False


def test_path_into_a_non_object_is_an_error():
    with pytest.raises(EvalError, match="'order.total' is a number, it has no field 'cents'"):
        evaluate("order.total.cents", {"order": {"total": 5}})
    with pytest.raises(EvalError, match="has no field"):
        evaluate("has(order.total.cents)", {"order": {"total": 5}})


def test_builtin_functions():
    assert evaluate("round(2.345, 2)") == Decimal("2.35")  # half up, not banker's
    assert evaluate("round(2.5)") == Decimal("3")
    assert evaluate("min(3, 1, 2)") == Decimal(1)
    assert evaluate("max([3, 9])") == Decimal(9)
    assert evaluate("sum(xs)", {"xs": [1, 2.5]}) == Decimal("3.5")
    assert evaluate("abs(-4)") == Decimal(4)
    assert evaluate('len("abc") + len([1])') == Decimal(4)
    assert evaluate('upper("a") + lower("B")') == "Ab"
    assert evaluate('starts_with("SKU-1", "SKU")') is True


@pytest.mark.parametrize(
    ("expr", "message"),
    [
        ("round(1, 0.5)", "non-negative whole number"),
        ('round("1")', "argument 1 must be a number"),
        ("max([])", "empty list"),
        ('sum([1, "x"])', "item 2 must be a number"),
        ("lower(1)", "must be a string"),
        ("len(true)", "string or list"),
    ],
)
def test_builtin_argument_errors_point_at_the_call(expr, message):
    with pytest.raises(EvalError, match=message) as info:
        evaluate(expr)
    assert info.value.span.start == 0
