from decimal import Decimal

import pytest

from rules_dsl import ParseError, RulesetSyntaxError, parse, parse_expression
from rules_dsl.nodes import (
    ArithOp,
    AssignOp,
    Binary,
    Call,
    Compare,
    CompareOp,
    Has,
    ListExpr,
    Literal,
    Logical,
    LogicOp,
    Path,
    SetAction,
    StopAction,
    TagAction,
    Unary,
    UnaryOp,
)
from rules_dsl.parser import MAX_NESTING


def num(text: str) -> Literal:
    return Literal(Decimal(text))


def test_multiplication_binds_tighter_than_addition():
    assert parse_expression("1 + 2 * 3") == Binary(
        ArithOp.ADD, num("1"), Binary(ArithOp.MUL, num("2"), num("3"))
    )


def test_arithmetic_is_left_associative():
    assert parse_expression("8 - 4 - 2") == Binary(
        ArithOp.SUB, Binary(ArithOp.SUB, num("8"), num("4")), num("2")
    )


def test_and_binds_tighter_than_or_and_not_tighter_than_and():
    a, b, c = Path(("a",)), Path(("b",)), Path(("c",))
    assert parse_expression("a or not b and c") == Logical(
        LogicOp.OR, a, Logical(LogicOp.AND, Unary(UnaryOp.NOT, b), c)
    )


def test_not_applies_to_a_whole_comparison():
    assert parse_expression("not x == 1") == Unary(
        UnaryOp.NOT, Compare(CompareOp.EQ, Path(("x",)), num("1"))
    )


def test_not_in_is_a_single_operator():
    assert parse_expression('x not in ["a"]') == Compare(
        CompareOp.NOT_IN, Path(("x",)), ListExpr((Literal("a"),))
    )


def test_primaries():
    assert parse_expression("customer.address.zip") == Path(("customer", "address", "zip"))
    assert parse_expression("has(customer.vip)") == Has(Path(("customer", "vip")))
    assert parse_expression("max(1, x)") == Call("max", (num("1"), Path(("x",))))
    assert parse_expression("len([])") == Call("len", (ListExpr(()),))
    assert parse_expression("-(1)") == Unary(UnaryOp.NEG, num("1"))
    assert parse_expression("true") == Literal(True)


def test_parenthesis_override_precedence():
    assert parse_expression("(1 + 2) * 3") == Binary(
        ArithOp.MUL, Binary(ArithOp.ADD, num("1"), num("2")), num("3")
    )


def test_chained_comparisons_are_rejected():
    with pytest.raises(ParseError, match="cannot be chained"):
        parse_expression("1 < x < 3")


def test_spans_cover_the_whole_expression():
    expr = parse_expression("a +  bb")
    assert (expr.span.start, expr.span.end) == (0, 7)


def test_full_rule():
    ruleset = parse(
        """
        rule "r" priority -5
        when x > 1
        then
            set total += x * 2
            tag "big"
            stop
        end
        """
    )
    (rule,) = ruleset.rules
    assert rule.name == "r" and rule.priority == Decimal(-5)
    assert rule.actions == (
        SetAction("total", AssignOp.ADD, Binary(ArithOp.MUL, Path(("x",)), num("2"))),
        TagAction("big"),
        StopAction(),
    )


def test_priority_defaults_to_zero_and_ties_keep_source_order():
    ruleset = parse(
        'rule "a" when true then stop end\n'
        'rule "b" priority 9 when true then stop end\n'
        'rule "c" when true then stop end'
    )
    assert [r.name for r in ruleset.in_execution_order()] == ["b", "a", "c"]


def test_error_recovery_reports_every_broken_rule():
    text = """
    rule "one" when x > then stop end
    rule "two" when true then stop end
    rule "three" when true then set = 1 end
    rule "four" when true then
    """
    with pytest.raises(RulesetSyntaxError) as info:
        parse(text)
    messages = [error.message for error in info.value.errors]
    assert len(messages) == 3
    assert "expected an expression" in messages[0]
    assert "result name after 'set'" in messages[1]
    assert "missing 'end'" in messages[2]


def test_missing_end_does_not_swallow_the_next_rule():
    text = 'rule "a" when true then stop\nrule "b" when true then stop end'
    with pytest.raises(RulesetSyntaxError) as info:
        parse(text)
    assert len(info.value.errors) == 1


def test_rule_needs_an_action():
    with pytest.raises(RulesetSyntaxError, match="1 syntax"):
        parse('rule "a" when true then end')


def test_garbage_before_rules_is_reported_not_looped_on():
    with pytest.raises(RulesetSyntaxError) as info:
        parse('when when rule "ok" when true then stop end')
    assert len(info.value.errors) == 1


def test_deep_nesting_is_a_clean_error_not_a_crash():
    with pytest.raises(ParseError, match="nested too deeply"):
        parse_expression("(" * (MAX_NESTING + 5) + "1" + ")" * (MAX_NESTING + 5))
    with pytest.raises(ParseError, match="nested too deeply"):
        parse_expression("not " * (MAX_NESTING + 5) + "true")


def test_comments_above_a_rule_are_attached():
    ruleset = parse('# about a\n\nrule "a" when true then stop end\n# the end\n')
    assert ruleset.rules[0].comments == ("# about a", "")
    assert ruleset.trailing_comments == ("# the end",)
