"""Canonical pretty-printer (``rules-dsl fmt``), written as a visitor.

The formatter inserts the *minimum* parentheses needed to reproduce the tree,
which is what makes the property ``parse(format(tree)) == tree`` hold (see
``tests/test_formatter.py``, which checks it on randomly generated trees).
"""

from __future__ import annotations

from decimal import Decimal

from .nodes import (
    ArithOp,
    Binary,
    Call,
    Compare,
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
from .visitor import NodeVisitor

INDENT = "    "

# Binding strength; higher binds tighter. Mirrors the grammar in parser.py.
PREC_OR, PREC_AND, PREC_NOT, PREC_COMPARE, PREC_ADD, PREC_MUL, PREC_NEG, PREC_ATOM = range(1, 9)


def quote(text: str) -> str:
    escaped = (
        text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
    )
    return f'"{escaped}"'


def precedence(expr: Expr) -> int:
    match expr:
        case Logical(op=LogicOp.OR):
            return PREC_OR
        case Logical():
            return PREC_AND
        case Unary(op=UnaryOp.NOT):
            return PREC_NOT
        case Compare():
            return PREC_COMPARE
        case Binary(op=ArithOp.ADD | ArithOp.SUB):
            return PREC_ADD
        case Binary():
            return PREC_MUL
        case Unary():
            return PREC_NEG
        case _:
            return PREC_ATOM


class Formatter(NodeVisitor):
    # -- expressions -------------------------------------------------------

    def _wrap(self, expr: Expr, needs_parens: bool) -> str:
        text = self.visit(expr)
        return f"({text})" if needs_parens else text

    def _infix(self, op: str, left: Expr, right: Expr, prec: int, associative: bool) -> str:
        # Left-associative operators: an equal-precedence child on the left is
        # implied by the grammar, one on the right needs explicit parentheses.
        # Non-associative operators (comparisons) parenthesise both sides.
        left_text = self._wrap(left, precedence(left) < prec + (0 if associative else 1))
        right_text = self._wrap(right, precedence(right) <= prec)
        return f"{left_text} {op} {right_text}"

    def visit_Literal(self, node: Literal) -> str:
        if isinstance(node.value, bool):
            return "true" if node.value else "false"
        if isinstance(node.value, Decimal):
            return node.text if node.text is not None else format(node.value, "f")
        return quote(node.value)

    def visit_ListExpr(self, node: ListExpr) -> str:
        return "[" + ", ".join(self.visit(item) for item in node.items) + "]"

    def visit_Path(self, node: Path) -> str:
        return node.dotted

    def visit_Has(self, node: Has) -> str:
        return f"has({node.path.dotted})"

    def visit_Call(self, node: Call) -> str:
        return f"{node.name}(" + ", ".join(self.visit(arg) for arg in node.args) + ")"

    def visit_Unary(self, node: Unary) -> str:
        if node.op is UnaryOp.NOT:
            return "not " + self._wrap(node.operand, precedence(node.operand) < PREC_NOT)
        return "-" + self._wrap(node.operand, precedence(node.operand) < PREC_NEG)

    def visit_Binary(self, node: Binary) -> str:
        return self._infix(str(node.op), node.left, node.right, precedence(node), True)

    def visit_Logical(self, node: Logical) -> str:
        return self._infix(str(node.op), node.left, node.right, precedence(node), True)

    def visit_Compare(self, node: Compare) -> str:
        return self._infix(str(node.op), node.left, node.right, PREC_COMPARE, False)

    # -- actions and rules -------------------------------------------------

    def visit_SetAction(self, node: SetAction) -> str:
        return f"set {node.name} {node.op} {self.visit(node.value)}"

    def visit_TagAction(self, node: TagAction) -> str:
        return f"tag {quote(node.tag)}"

    def visit_StopAction(self, node: StopAction) -> str:
        return "stop"

    def visit_Rule(self, node: Rule) -> str:
        header = f"rule {quote(node.name)}"
        if node.priority != 0:
            header += f" priority {format(node.priority, 'f')}"
        lines = [*node.comments, header, "when", INDENT + self.visit(node.condition), "then"]
        lines += [INDENT + self.visit(action) for action in node.actions]
        lines.append("end")
        return "\n".join(lines)

    def visit_RuleSet(self, node: RuleSet) -> str:
        blocks = [self.visit(rule) for rule in node.rules]
        if node.trailing_comments:
            blocks.append("\n".join(node.trailing_comments))
        return "\n\n".join(blocks) + "\n" if blocks else ""


def format_ruleset(ruleset: RuleSet) -> str:
    return Formatter().visit(ruleset)


def format_expression(expr: Expr) -> str:
    return Formatter().visit(expr)
