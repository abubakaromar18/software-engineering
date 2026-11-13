"""Recursive-descent parser producing the AST in :mod:`rules_dsl.nodes`.

Grammar (EBNF, lowest precedence first)::

    ruleset     = { rule } EOF ;
    rule        = "rule" STRING [ "priority" [ "-" ] NUMBER ]
                  "when" expr "then" action { action } "end" ;
    action      = "set" IDENT ( "=" | "+=" | "-=" ) expr
                | "tag" STRING
                | "stop" ;
    expr        = and_expr { "or" and_expr } ;
    and_expr    = not_expr { "and" not_expr } ;
    not_expr    = "not" not_expr | comparison ;
    comparison  = additive [ compare_op additive ] ;      (* non-associative *)
    compare_op  = "==" | "!=" | "<" | "<=" | ">" | ">=" | "in" | "not" "in" ;
    additive    = term { ( "+" | "-" ) term } ;
    term        = unary { ( "*" | "/" ) unary } ;
    unary       = "-" unary | primary ;
    primary     = NUMBER | STRING | "true" | "false"
                | "[" [ expr { "," expr } ] "]"
                | "(" expr ")"
                | "has" "(" path ")"
                | IDENT "(" [ expr { "," expr } ] ")"
                | path ;
    path        = IDENT { "." IDENT } ;

One method per production keeps the code a direct transcription of the grammar.
Comments above a rule are attached to it so the formatter can keep them;
comments inside a rule body are discarded.
On a syntax error the parser records it and resynchronises at the next ``rule``
keyword, so one run reports every broken rule instead of only the first.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from decimal import Decimal

from .errors import DslError, ParseError, RulesetSyntaxError
from .lexer import Lexer
from .nodes import (
    Action,
    ArithOp,
    AssignOp,
    Binary,
    Call,
    Compare,
    CompareOp,
    Expr,
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
from .source import Source, Span
from .tokens import Token, TokenKind

MAX_NESTING = 100  # guards Python's recursion limit against hostile input

COMPARE_OPS = {
    TokenKind.EQ: CompareOp.EQ,
    TokenKind.NE: CompareOp.NE,
    TokenKind.LT: CompareOp.LT,
    TokenKind.LE: CompareOp.LE,
    TokenKind.GT: CompareOp.GT,
    TokenKind.GE: CompareOp.GE,
    TokenKind.IN: CompareOp.IN,
}
ADDITIVE_OPS = {TokenKind.PLUS: ArithOp.ADD, TokenKind.MINUS: ArithOp.SUB}
TERM_OPS = {TokenKind.STAR: ArithOp.MUL, TokenKind.SLASH: ArithOp.DIV}
ASSIGN_OPS = {
    TokenKind.ASSIGN: AssignOp.SET,
    TokenKind.PLUS_ASSIGN: AssignOp.ADD,
    TokenKind.MINUS_ASSIGN: AssignOp.SUB,
}


class Parser:
    def __init__(self, tokens: list[Token], comments: list[tuple[Span, str]] | None = None) -> None:
        self._tokens = tokens
        self._comments = comments or []
        self._next_comment = 0
        self._pos = 0
        self._depth = 0

    # -- entry points ------------------------------------------------------

    def parse_ruleset(self) -> RuleSet:
        rules: list[Rule] = []
        errors: list[DslError] = []
        start_span = self._current.span
        while not self._check(TokenKind.EOF):
            start = self._pos
            leading = self._take_comments()
            try:
                rule = self._rule()
                self._drop_comments_before(rule.span.end if rule.span else 0)
                rules.append(replace(rule, comments=leading))
            except ParseError as error:
                errors.append(error)
                self._synchronize(start)
        if errors:
            raise RulesetSyntaxError(errors)
        trailing = self._take_comments()  # current is EOF
        return RuleSet(tuple(rules), trailing_comments=trailing, span=start_span)

    def parse_expression(self) -> Expr:
        expr = self._expression()
        self._expect(TokenKind.EOF, "end of expression")
        return expr

    # -- token helpers -----------------------------------------------------

    @property
    def _current(self) -> Token:
        return self._tokens[self._pos]

    def _peek(self, offset: int = 1) -> Token:
        return self._tokens[min(self._pos + offset, len(self._tokens) - 1)]

    def _check(self, kind: TokenKind) -> bool:
        return self._current.kind is kind

    def _advance(self) -> Token:
        token = self._current
        if token.kind is not TokenKind.EOF:
            self._pos += 1
        return token

    def _match(self, kind: TokenKind) -> Token | None:
        return self._advance() if self._check(kind) else None

    def _expect(self, kind: TokenKind, what: str) -> Token:
        if self._check(kind):
            return self._advance()
        raise ParseError(f"expected {what}, found {self._current.describe()}", self._current.span)

    def _take_comments(self) -> tuple[str, ...]:
        """Consume the comments that precede the current token.

        A blank line in the source becomes an empty string, so the formatter can
        keep a file-header comment visually separate from the first rule.
        """
        before = self._current.span
        taken: list[str] = []
        last_line: int | None = None
        while (
            self._next_comment < len(self._comments)
            and self._comments[self._next_comment][0].start < before.start
        ):
            span, text = self._comments[self._next_comment]
            if last_line is not None and span.line > last_line + 1:
                taken.append("")
            taken.append(text)
            last_line = span.line
            self._next_comment += 1
        if last_line is not None and before.line > last_line + 1 and not self._check(TokenKind.EOF):
            taken.append("")
        return tuple(taken)

    def _drop_comments_before(self, offset: int) -> None:
        """Discard comments inside a rule body; only leading comments are kept."""
        while (
            self._next_comment < len(self._comments)
            and self._comments[self._next_comment][0].start < offset
        ):
            self._next_comment += 1

    def _synchronize(self, rule_start: int) -> None:
        """Skip to the next ``rule`` keyword, always making progress."""
        if self._pos == rule_start:
            self._advance()
        while not (self._check(TokenKind.RULE) or self._check(TokenKind.EOF)):
            self._advance()

    @contextmanager
    def _nested(self) -> Iterator[None]:
        self._depth += 1
        try:
            if self._depth > MAX_NESTING:
                raise ParseError("expression is nested too deeply", self._current.span)
            yield
        finally:
            self._depth -= 1

    def _span_since(self, start: Span) -> Span:
        return start.to(self._tokens[max(self._pos - 1, 0)].span)

    # -- rules and actions -------------------------------------------------

    def _rule(self) -> Rule:
        keyword = self._expect(TokenKind.RULE, "'rule'")
        name = self._expect(TokenKind.STRING, "a rule name in double quotes")
        priority = Decimal(0)
        if self._match(TokenKind.PRIORITY):
            negative = self._match(TokenKind.MINUS) is not None
            number = self._expect(TokenKind.NUMBER, "a priority number")
            priority = -number.value if negative else number.value  # type: ignore[operator,assignment]
        self._expect(TokenKind.WHEN, "'when'")
        condition = self._expression()
        self._expect(TokenKind.THEN, "'then' after the condition")
        actions: list[Action] = []
        while not self._check(TokenKind.END):
            if self._check(TokenKind.EOF) or self._check(TokenKind.RULE):
                raise ParseError(f"rule \"{name.value}\" is missing 'end'", self._current.span)
            actions.append(self._action())
        if not actions:
            raise ParseError("a rule needs at least one action", self._current.span)
        self._advance()  # 'end'
        return Rule(
            str(name.value),
            priority,
            condition,
            tuple(actions),
            span=self._span_since(keyword.span),
        )

    def _action(self) -> Action:
        token = self._current
        if self._match(TokenKind.SET):
            target = self._expect(TokenKind.IDENT, "a result name after 'set'")
            op_token = self._current
            if op_token.kind not in ASSIGN_OPS:
                raise ParseError(
                    f"expected '=', '+=' or '-=', found {op_token.describe()}", op_token.span
                )
            self._advance()
            value = self._expression()
            return SetAction(
                str(target.value),
                ASSIGN_OPS[op_token.kind],
                value,
                span=self._span_since(token.span),
            )
        if self._match(TokenKind.TAG):
            tag = self._expect(TokenKind.STRING, "a tag in double quotes")
            return TagAction(str(tag.value), span=self._span_since(token.span))
        if self._match(TokenKind.STOP):
            return StopAction(span=token.span)
        raise ParseError(
            f"expected an action ('set', 'tag' or 'stop') or 'end', found {token.describe()}",
            token.span,
        )

    # -- expressions, lowest precedence first ------------------------------

    def _expression(self) -> Expr:
        with self._nested():
            return self._or()

    def _or(self) -> Expr:
        left = self._and()
        while self._match(TokenKind.OR):
            right = self._and()
            left = Logical(LogicOp.OR, left, right, span=self._join(left, right))
        return left

    def _and(self) -> Expr:
        left = self._not()
        while self._match(TokenKind.AND):
            right = self._not()
            left = Logical(LogicOp.AND, left, right, span=self._join(left, right))
        return left

    def _not(self) -> Expr:
        token = self._match(TokenKind.NOT)
        if token is None:
            return self._comparison()
        with self._nested():
            operand = self._not()
        return Unary(UnaryOp.NOT, operand, span=self._span_since(token.span))

    def _compare_op(self) -> CompareOp | None:
        """Consume a comparison operator if present (``not in`` is two tokens)."""
        if self._check(TokenKind.NOT) and self._peek().kind is TokenKind.IN:
            self._advance()
            self._advance()
            return CompareOp.NOT_IN
        op = COMPARE_OPS.get(self._current.kind)
        if op is not None:
            self._advance()
        return op

    def _comparison(self) -> Expr:
        left = self._additive()
        op = self._compare_op()
        if op is None:
            return left
        right = self._additive()
        if self._current.kind in COMPARE_OPS or (
            self._check(TokenKind.NOT) and self._peek().kind is TokenKind.IN
        ):
            raise ParseError(
                "comparisons cannot be chained; combine them with 'and'", self._current.span
            )
        return Compare(op, left, right, span=self._join(left, right))

    def _additive(self) -> Expr:
        left = self._term()
        while (op := ADDITIVE_OPS.get(self._current.kind)) is not None:
            self._advance()
            right = self._term()
            left = Binary(op, left, right, span=self._join(left, right))
        return left

    def _term(self) -> Expr:
        left = self._unary()
        while (op := TERM_OPS.get(self._current.kind)) is not None:
            self._advance()
            right = self._unary()
            left = Binary(op, left, right, span=self._join(left, right))
        return left

    def _unary(self) -> Expr:
        token = self._match(TokenKind.MINUS)
        if token is None:
            return self._primary()
        with self._nested():
            operand = self._unary()
        return Unary(UnaryOp.NEG, operand, span=self._span_since(token.span))

    def _primary(self) -> Expr:
        token = self._current
        match token.kind:
            case TokenKind.NUMBER:
                self._advance()
                return Literal(token.value, text=token.lexeme, span=token.span)  # type: ignore[arg-type]
            case TokenKind.STRING:
                self._advance()
                return Literal(token.value, span=token.span)  # type: ignore[arg-type]
            case TokenKind.TRUE | TokenKind.FALSE:
                self._advance()
                return Literal(token.kind is TokenKind.TRUE, span=token.span)
            case TokenKind.LPAREN:
                self._advance()
                inner = self._expression()
                self._expect(TokenKind.RPAREN, "')'")
                return inner
            case TokenKind.LBRACKET:
                self._advance()
                items = self._arguments(TokenKind.RBRACKET, "']'")
                return ListExpr(items, span=self._span_since(token.span))
            case TokenKind.HAS:
                self._advance()
                self._expect(TokenKind.LPAREN, "'(' after 'has'")
                path = self._path()
                self._expect(TokenKind.RPAREN, "')' after the path")
                return Has(path, span=self._span_since(token.span))
            case TokenKind.IDENT if self._peek().kind is TokenKind.LPAREN:
                self._advance()
                self._advance()
                args = self._arguments(TokenKind.RPAREN, "')'")
                return Call(str(token.value), args, span=self._span_since(token.span))
            case TokenKind.IDENT:
                return self._path()
        raise ParseError(f"expected an expression, found {token.describe()}", token.span)

    def _arguments(self, closer: TokenKind, closer_text: str) -> tuple[Expr, ...]:
        items: list[Expr] = []
        if self._match(closer):
            return ()
        while True:
            items.append(self._expression())
            if self._match(closer):
                return tuple(items)
            self._expect(TokenKind.COMMA, f"',' or {closer_text}")

    def _path(self) -> Path:
        first = self._expect(TokenKind.IDENT, "a fact name")
        parts = [str(first.value)]
        while self._match(TokenKind.DOT):
            parts.append(str(self._expect(TokenKind.IDENT, "a field name after '.'").value))
        return Path(tuple(parts), span=self._span_since(first.span))

    @staticmethod
    def _join(left: Expr, right: Expr) -> Span | None:
        if left.span is None or right.span is None:
            return left.span or right.span
        return left.span.to(right.span)


def _source(text: Source | str) -> Source:
    return Source(text) if isinstance(text, str) else text


def parse(text: Source | str) -> RuleSet:
    """Parse a whole ruleset. Raises :class:`LexError` or :class:`RulesetSyntaxError`."""
    lexer = Lexer(_source(text))
    tokens = lexer.tokenize()
    return Parser(tokens, lexer.comments).parse_ruleset()


def parse_expression(text: Source | str) -> Expr:
    """Parse a single expression (handy for tests and REPL-style tools)."""
    return Parser(Lexer(_source(text)).tokenize()).parse_expression()
