"""A parsed Python file plus the token-level facts detectors need.

The ``ast`` drops comments and blank lines, so "how long is this function?"
can't be answered from the tree alone. ``SourceFile`` tokenizes the text once
and records which physical lines carry code and which carry suppression
comments; every detector then shares that work.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from dataclasses import dataclass
from pathlib import Path

# "# smell: ignore" suppresses every rule on that line;
# "# smell: ignore[long-method, deep-nesting]" suppresses only those rules.
_SUPPRESS = re.compile(r"#\s*smell:\s*ignore(?:\[(?P<rules>[\w\s,-]+)\])?")
ALL_RULES = "*"

_NON_CODE_TOKENS = {
    tokenize.COMMENT,
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENCODING,
    tokenize.ENDMARKER,
}


@dataclass(frozen=True)
class SourceFile:
    path: Path
    tree: ast.Module
    code_lines: frozenset[int]
    suppressions: dict[int, frozenset[str]]

    @classmethod
    def parse(cls, path: Path, text: str) -> SourceFile:
        """Parse ``text``. Raises ``SyntaxError`` for invalid Python."""
        tree = ast.parse(text, filename=str(path))
        code_lines: set[int] = set()
        suppressions: dict[int, frozenset[str]] = {}
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT:
                match = _SUPPRESS.search(token.string)
                if match:
                    suppressions[token.start[0]] = _parse_rules(match.group("rules"))
            elif token.type not in _NON_CODE_TOKENS:
                # A multi-line token (e.g. a triple-quoted string) covers every line it spans.
                code_lines.update(range(token.start[0], token.end[0] + 1))
        return cls(path, tree, frozenset(code_lines), suppressions)

    @classmethod
    def read(cls, path: Path) -> SourceFile:
        # tokenize.open honours PEP 263 encoding declarations.
        with tokenize.open(path) as handle:
            return cls.parse(path, handle.read())

    def count_code_lines(self, start: int, end: int, exclude: range | None = None) -> int:
        """Lines in ``[start, end]`` that contain code, ignoring blanks and comments."""
        return sum(
            1
            for line in range(start, end + 1)
            if line in self.code_lines and (exclude is None or line not in exclude)
        )

    def is_suppressed(self, line: int, rule: str) -> bool:
        rules = self.suppressions.get(line)
        return rules is not None and (ALL_RULES in rules or rule in rules)


def docstring_lines(node: ast.AST) -> range | None:
    """The line range of a function/class/module docstring, if it has one."""
    body = getattr(node, "body", None)
    if not body:
        return None
    first = body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return range(first.lineno, (first.end_lineno or first.lineno) + 1)
    return None


def _parse_rules(spec: str | None) -> frozenset[str]:
    if spec is None:
        return frozenset({ALL_RULES})
    return frozenset(rule.strip() for rule in spec.split(",") if rule.strip())
