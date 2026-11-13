"""Token kinds produced by the lexer and consumed by the parser."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, auto

from .source import Span


class TokenKind(Enum):
    # Literals and names
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()
    # Keywords
    RULE = auto()
    PRIORITY = auto()
    WHEN = auto()
    THEN = auto()
    END = auto()
    SET = auto()
    TAG = auto()
    STOP = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    IN = auto()
    HAS = auto()
    TRUE = auto()
    FALSE = auto()
    # Punctuation
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    DOT = auto()
    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    ASSIGN = auto()
    PLUS_ASSIGN = auto()
    MINUS_ASSIGN = auto()
    EOF = auto()


KEYWORDS: dict[str, TokenKind] = {
    "rule": TokenKind.RULE,
    "priority": TokenKind.PRIORITY,
    "when": TokenKind.WHEN,
    "then": TokenKind.THEN,
    "end": TokenKind.END,
    "set": TokenKind.SET,
    "tag": TokenKind.TAG,
    "stop": TokenKind.STOP,
    "and": TokenKind.AND,
    "or": TokenKind.OR,
    "not": TokenKind.NOT,
    "in": TokenKind.IN,
    "has": TokenKind.HAS,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
}

# Longest match first: two-character operators are tried before one-character ones.
OPERATORS: dict[str, TokenKind] = {
    "==": TokenKind.EQ,
    "!=": TokenKind.NE,
    "<=": TokenKind.LE,
    ">=": TokenKind.GE,
    "+=": TokenKind.PLUS_ASSIGN,
    "-=": TokenKind.MINUS_ASSIGN,
    "<": TokenKind.LT,
    ">": TokenKind.GT,
    "=": TokenKind.ASSIGN,
    "+": TokenKind.PLUS,
    "-": TokenKind.MINUS,
    "*": TokenKind.STAR,
    "/": TokenKind.SLASH,
    "(": TokenKind.LPAREN,
    ")": TokenKind.RPAREN,
    "[": TokenKind.LBRACKET,
    "]": TokenKind.RBRACKET,
    ",": TokenKind.COMMA,
    ".": TokenKind.DOT,
}


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    lexeme: str
    span: Span
    value: Decimal | str | None = None

    def describe(self) -> str:
        """Human-readable form for error messages."""
        if self.kind is TokenKind.EOF:
            return "end of input"
        return f"'{self.lexeme}'"
