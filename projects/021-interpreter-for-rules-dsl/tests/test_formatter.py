"""The formatter must be the parser's inverse: parse(format(tree)) == tree."""

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from rules_dsl import format_expression, format_ruleset, parse, parse_expression
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
    Rule,
    RuleSet,
    SetAction,
    StopAction,
    TagAction,
    Unary,
    UnaryOp,
)
from rules_dsl.tokens import KEYWORDS


def roundtrip(text: str) -> str:
    return format_expression(parse_expression(text))


def test_minimal_parentheses():
    assert roundtrip("((a + b)) * c") == "(a + b) * c"
    assert roundtrip("a + (b * c)") == "a + b * c"
    assert roundtrip("a - (b - c)") == "a - (b - c)"
    assert roundtrip("(a - b) - c") == "a - b - c"
    assert roundtrip("not (a and b)") == "not (a and b)"
    assert roundtrip("(not a) and b") == "not a and b"
    assert roundtrip("(a == b) == c") == "(a == b) == c"
    assert roundtrip("-(a + b)") == "-(a + b)"
    assert roundtrip("a or (b or c)") == "a or (b or c)"


def test_literals_keep_their_spelling():
    assert roundtrip('[10%, 2.50, "q\\"\\n"]') == '[10%, 2.50, "q\\"\\n"]'


def test_examples_are_already_canonical(examples):
    for path in examples.glob("*.rules"):
        text = path.read_text()
        assert format_ruleset(parse(text)) == text, path.name


def test_formatting_is_idempotent_on_messy_input():
    messy = '# hi\nrule "a"   priority 3 when (x>1)and(y<2) then set z=x+1 tag "t" stop end'
    once = format_ruleset(parse(messy))
    assert once == (
        "# hi\n"
        'rule "a" priority 3\nwhen\n    x > 1 and y < 2\nthen\n'
        '    set z = x + 1\n    tag "t"\n    stop\nend\n'
    )
    assert format_ruleset(parse(once)) == once


# -- property-based round trip ---------------------------------------------

names = st.from_regex(r"[a-z_][a-z0-9_]{0,6}", fullmatch=True).filter(
    lambda name: name not in KEYWORDS
)
numbers = st.decimals(min_value=0, max_value=10**6, places=2, allow_nan=False).map(
    lambda d: Literal(d)
)
strings = st.text(
    st.characters(codec="utf-8", exclude_categories=("Cs", "Cc"))
    | st.sampled_from(['"', "\\", "\n", "\t"]),
    max_size=8,
).map(Literal)
booleans = st.booleans().map(Literal)
paths = st.lists(names, min_size=1, max_size=3).map(lambda parts: Path(tuple(parts)))
leaves = numbers | strings | booleans | paths | paths.map(Has)


def extend(children: st.SearchStrategy) -> st.SearchStrategy:
    return st.one_of(
        st.builds(Binary, st.sampled_from(ArithOp), children, children),
        st.builds(Logical, st.sampled_from(LogicOp), children, children),
        st.builds(Compare, st.sampled_from(CompareOp), children, children),
        st.builds(Unary, st.sampled_from(UnaryOp), children),
        st.builds(Call, names, st.lists(children, max_size=3).map(tuple)),
        st.lists(children, max_size=3).map(lambda items: ListExpr(tuple(items))),
    )


expressions = st.recursive(leaves, extend, max_leaves=25)
actions = st.one_of(
    st.builds(SetAction, names, st.sampled_from(AssignOp), expressions),
    st.builds(TagAction, st.text(max_size=5)),
    st.just(StopAction()),
)
rules = st.builds(
    Rule,
    st.text(max_size=10),
    st.integers(-50, 50).map(Decimal),
    expressions,
    st.lists(actions, min_size=1, max_size=4).map(tuple),
)


@settings(max_examples=300, deadline=None)
@given(expressions)
def test_expression_roundtrip(expr):
    assert parse_expression(format_expression(expr)) == expr


@settings(max_examples=100, deadline=None)
@given(st.lists(rules, max_size=4).map(lambda rs: RuleSet(tuple(rs))))
def test_ruleset_roundtrip(ruleset):
    assert parse(format_ruleset(ruleset)) == ruleset
