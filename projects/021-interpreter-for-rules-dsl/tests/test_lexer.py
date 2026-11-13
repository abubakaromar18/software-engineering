from decimal import Decimal

import pytest

from rules_dsl import LexError
from rules_dsl.lexer import Lexer, tokenize
from rules_dsl.source import Source
from rules_dsl.tokens import TokenKind as K


def kinds(text: str) -> list[K]:
    return [token.kind for token in tokenize(text)]


def test_keywords_identifiers_and_operators():
    assert kinds("rule when x.y >= 3 and not z then end") == [
        K.RULE, K.WHEN, K.IDENT, K.DOT, K.IDENT, K.GE, K.NUMBER,
        K.AND, K.NOT, K.IDENT, K.THEN, K.END, K.EOF,
    ]  # fmt: skip


def test_two_character_operators_win_over_one_character():
    assert kinds("== != <= >= += -= = < >")[:-1] == [
        K.EQ, K.NE, K.LE, K.GE, K.PLUS_ASSIGN, K.MINUS_ASSIGN, K.ASSIGN, K.LT, K.GT,
    ]  # fmt: skip


def test_numbers_are_exact_decimals_and_percent_divides_by_100():
    tokens = tokenize("12 3.50 10% 2.5%")
    assert [t.value for t in tokens[:-1]] == [
        Decimal("12"),
        Decimal("3.50"),
        Decimal("0.1"),
        Decimal("0.025"),
    ]
    assert tokens[2].lexeme == "10%"


def test_string_escapes():
    (token, _eof) = tokenize(r'"say \"hi\"\n\tback\\slash"')
    assert token.value == 'say "hi"\n\tback\\slash'


def test_comments_are_skipped_but_recorded():
    lexer = Lexer(Source("# header\nrule # trailing\n"))
    assert [t.kind for t in lexer.tokenize()] == [K.RULE, K.EOF]
    assert [text for _span, text in lexer.comments] == ["# header", "# trailing"]


def test_positions_track_lines_and_columns():
    tokens = tokenize("rule\n  when")
    assert (tokens[1].span.line, tokens[1].span.column) == (2, 3)


@pytest.mark.parametrize(
    ("text", "message", "column"),
    [
        ('"open', "unterminated string", 1),
        ('"a\nb"', "unterminated string", 1),
        (r'"bad \q"', "unknown escape", 6),
        ("x @ y", "unexpected character '@'", 3),
        ("3abc", "cannot start with a digit", 1),
    ],
)
def test_lex_errors_have_positions(text, message, column):
    with pytest.raises(LexError, match=message) as info:
        tokenize(text)
    assert info.value.span.column == column


def test_unicode_digits_are_not_numbers():
    with pytest.raises(LexError):
        tokenize("²")
