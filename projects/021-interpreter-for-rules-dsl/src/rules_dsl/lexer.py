"""Hand-written scanner turning rules text into a list of tokens.

A hand-written lexer (rather than a regex table) keeps error positions exact and
makes the two language-specific rules easy to express: ``10%`` is a percent
literal meaning ``0.10``, and strings support a small, explicit escape set.
"""

from __future__ import annotations

from decimal import Decimal

from .errors import LexError
from .source import Source, Span
from .tokens import KEYWORDS, OPERATORS, Token, TokenKind


def _is_digit(char: str) -> bool:
    # str.isdigit() accepts characters such as "²" that Decimal cannot parse.
    return len(char) == 1 and "0" <= char <= "9"


ESCAPES = {'"': '"', "\\": "\\", "n": "\n", "t": "\t"}


class Lexer:
    def __init__(self, source: Source) -> None:
        self._text = source.text
        self._pos = 0
        self._line = 1
        self._line_start = 0
        self.comments: list[tuple[Span, str]] = []

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while True:
            self._skip_trivia()
            if self._pos >= len(self._text):
                tokens.append(Token(TokenKind.EOF, "", self._span_from(self._pos)))
                return tokens
            tokens.append(self._next_token())

    # -- scanning helpers --------------------------------------------------

    def _peek(self, offset: int = 0) -> str:
        index = self._pos + offset
        return self._text[index] if index < len(self._text) else ""

    def _span_from(self, start: int, line: int | None = None, column: int | None = None) -> Span:
        line = self._line if line is None else line
        column = start - self._line_start + 1 if column is None else column
        return Span(start, max(self._pos, start + 1), line, column)

    def _skip_trivia(self) -> None:
        """Skip whitespace and ``#`` comments, tracking line numbers."""
        while self._pos < len(self._text):
            char = self._text[self._pos]
            if char == "\n":
                self._pos += 1
                self._line += 1
                self._line_start = self._pos
            elif char.isspace():
                self._pos += 1
            elif char == "#":
                start = self._pos
                while self._pos < len(self._text) and self._text[self._pos] != "\n":
                    self._pos += 1
                self.comments.append((self._span_from(start), self._text[start : self._pos]))
            else:
                return

    def _next_token(self) -> Token:
        char = self._peek()
        if _is_digit(char):
            return self._number()
        if char == '"':
            return self._string()
        if char.isalpha() or char == "_":
            return self._identifier()
        for lexeme in (self._text[self._pos : self._pos + 2], char):
            kind = OPERATORS.get(lexeme)
            if kind is not None:
                start = self._pos
                self._pos += len(lexeme)
                return Token(kind, lexeme, self._span_from(start))
        start = self._pos
        self._pos += 1
        raise LexError(f"unexpected character {char!r}", self._span_from(start))

    def _number(self) -> Token:
        start = self._pos
        while _is_digit(self._peek()):
            self._pos += 1
        if self._peek() == "." and _is_digit(self._peek(1)):
            self._pos += 1
            while _is_digit(self._peek()):
                self._pos += 1
        digits = self._text[start : self._pos]
        value = Decimal(digits)
        if self._peek() == "%":
            self._pos += 1
            value = value / 100
        if self._peek().isalpha() or self._peek() == "_":
            raise LexError("identifiers cannot start with a digit", self._span_from(start))
        return Token(TokenKind.NUMBER, self._text[start : self._pos], self._span_from(start), value)

    def _string(self) -> Token:
        start, line, column = self._pos, self._line, self._pos - self._line_start + 1
        self._pos += 1  # opening quote
        chars: list[str] = []
        while True:
            char = self._peek()
            if char in ("", "\n"):
                raise LexError("unterminated string", self._span_from(start, line, column))
            self._pos += 1
            if char == '"':
                break
            if char == "\\":
                escaped = self._peek()
                if escaped not in ESCAPES:
                    raise LexError(
                        f"unknown escape sequence '\\{escaped}'", self._span_from(self._pos - 1)
                    )
                self._pos += 1
                chars.append(ESCAPES[escaped])
            else:
                chars.append(char)
        lexeme = self._text[start : self._pos]
        return Token(TokenKind.STRING, lexeme, self._span_from(start, line, column), "".join(chars))

    def _identifier(self) -> Token:
        start = self._pos
        while self._peek().isalnum() or self._peek() == "_":
            self._pos += 1
        word = self._text[start : self._pos]
        kind = KEYWORDS.get(word, TokenKind.IDENT)
        return Token(kind, word, self._span_from(start), word if kind is TokenKind.IDENT else None)


def tokenize(source: Source | str) -> list[Token]:
    """Convenience wrapper: tokenize a :class:`Source` or a plain string."""
    if isinstance(source, str):
        source = Source(source)
    return Lexer(source).tokenize()
