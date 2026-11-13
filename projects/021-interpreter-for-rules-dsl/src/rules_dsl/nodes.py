"""Abstract syntax tree, with evaluation built into the nodes.

This is the heart of the Interpreter pattern (GoF): the grammar is mirrored by a
class hierarchy, terminal expressions (:class:`Literal`, :class:`Path`) and
non-terminal expressions (:class:`Binary`, :class:`Logical`...) each implement
``evaluate(context)``, and evaluating a tree is just calling ``evaluate`` on its
root. Operations other than evaluation (checking, formatting) are written as
visitors in separate modules so they do not bloat the node classes.

Nodes are immutable. Spans are excluded from equality so that two trees parsed
from differently formatted text compare equal.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal, DivisionByZero, InvalidOperation
from enum import StrEnum
from typing import TYPE_CHECKING

from .errors import EvalError
from .values import Value, display, is_number, type_name, values_equal

if TYPE_CHECKING:
    from .runtime import EvalContext
    from .source import Span


class ArithOp(StrEnum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"


class CompareOp(StrEnum):
    EQ = "=="
    NE = "!="
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="
    IN = "in"
    NOT_IN = "not in"


class LogicOp(StrEnum):
    AND = "and"
    OR = "or"


class UnaryOp(StrEnum):
    NEG = "-"
    NOT = "not"


class AssignOp(StrEnum):
    SET = "="
    ADD = "+="
    SUB = "-="


@dataclass(frozen=True)
class Node:
    span: Span | None = field(default=None, compare=False, repr=False, kw_only=True)

    def fail(self, message: str) -> EvalError:
        return EvalError(message, self.span)


# -- expressions -----------------------------------------------------------


@dataclass(frozen=True)
class Expr(Node, ABC):
    @abstractmethod
    def evaluate(self, context: EvalContext) -> Value: ...

    def evaluate_bool(self, context: EvalContext, role: str) -> bool:
        """Evaluate and insist on a boolean: the language has no truthiness."""
        value = self.evaluate(context)
        if not isinstance(value, bool):
            raise self.fail(f"{role} must be a boolean, got {type_name(value)} {display(value)}")
        return value


@dataclass(frozen=True)
class Literal(Expr):
    value: Decimal | str | bool
    # Original spelling of a number (e.g. "10%"), kept so the formatter preserves it.
    text: str | None = field(default=None, compare=False, repr=False, kw_only=True)

    def evaluate(self, context: EvalContext) -> Value:
        return self.value


@dataclass(frozen=True)
class ListExpr(Expr):
    items: tuple[Expr, ...]

    def evaluate(self, context: EvalContext) -> Value:
        return [item.evaluate(context) for item in self.items]


@dataclass(frozen=True)
class Path(Expr):
    """A dotted reference into the facts, e.g. ``customer.address.country``."""

    parts: tuple[str, ...]

    @property
    def dotted(self) -> str:
        return ".".join(self.parts)

    def resolve(self, context: EvalContext) -> tuple[bool, Value]:
        found, value = context.root(self.parts[0])
        if not found:
            return False, None
        for index, part in enumerate(self.parts[1:], start=1):
            if not isinstance(value, dict):
                prefix = ".".join(self.parts[:index])
                raise self.fail(f"'{prefix}' is a {type_name(value)}, it has no field '{part}'")
            if part not in value:
                return False, None
            value = value[part]
        return True, value

    def evaluate(self, context: EvalContext) -> Value:
        found, value = self.resolve(context)
        if not found:
            raise self.fail(f"unknown fact '{self.dotted}' (use has({self.dotted}) to test)")
        return value


@dataclass(frozen=True)
class Has(Expr):
    """``has(path)``: a special form, not a function, because its argument is not evaluated."""

    path: Path

    def evaluate(self, context: EvalContext) -> Value:
        found, _ = self.path.resolve(context)
        return found


@dataclass(frozen=True)
class Unary(Expr):
    op: UnaryOp
    operand: Expr

    def evaluate(self, context: EvalContext) -> Value:
        if self.op is UnaryOp.NOT:
            return not self.operand.evaluate_bool(context, "operand of 'not'")
        value = self.operand.evaluate(context)
        if not is_number(value):
            raise self.fail(f"cannot negate a {type_name(value)}")
        return -value  # type: ignore[operator]


@dataclass(frozen=True)
class Binary(Expr):
    op: ArithOp
    left: Expr
    right: Expr

    def evaluate(self, context: EvalContext) -> Value:
        left = self.left.evaluate(context)
        right = self.right.evaluate(context)
        if self.op is ArithOp.ADD and isinstance(left, str) and isinstance(right, str):
            return left + right
        if not (is_number(left) and is_number(right)):
            raise self.fail(
                f"operator '{self.op}' needs two numbers"
                f"{' or two strings' if self.op is ArithOp.ADD else ''}, "
                f"got {type_name(left)} and {type_name(right)}"
            )
        try:
            match self.op:
                case ArithOp.ADD:
                    return left + right  # type: ignore[operator]
                case ArithOp.SUB:
                    return left - right  # type: ignore[operator]
                case ArithOp.MUL:
                    return left * right  # type: ignore[operator]
                case ArithOp.DIV:
                    return left / right  # type: ignore[operator]
        except (DivisionByZero, InvalidOperation) as error:
            raise self.fail("division by zero") from error
        raise AssertionError(f"unhandled operator {self.op}")  # pragma: no cover


@dataclass(frozen=True)
class Logical(Expr):
    """``and`` / ``or`` with short-circuit evaluation."""

    op: LogicOp
    left: Expr
    right: Expr

    def evaluate(self, context: EvalContext) -> Value:
        left = self.left.evaluate_bool(context, f"left operand of '{self.op}'")
        if (self.op is LogicOp.AND and not left) or (self.op is LogicOp.OR and left):
            return left
        return self.right.evaluate_bool(context, f"right operand of '{self.op}'")


@dataclass(frozen=True)
class Compare(Expr):
    op: CompareOp
    left: Expr
    right: Expr

    def evaluate(self, context: EvalContext) -> Value:
        left = self.left.evaluate(context)
        right = self.right.evaluate(context)
        match self.op:
            case CompareOp.EQ:
                return values_equal(left, right)
            case CompareOp.NE:
                return not values_equal(left, right)
            case CompareOp.IN:
                return self._contains(right, left)
            case CompareOp.NOT_IN:
                return not self._contains(right, left)
        ordered = (is_number(left) and is_number(right)) or (
            isinstance(left, str) and isinstance(right, str)
        )
        if not ordered:
            raise self.fail(
                f"cannot compare {type_name(left)} {self.op} {type_name(right)}; "
                "ordering needs two numbers or two strings"
            )
        match self.op:
            case CompareOp.LT:
                return left < right  # type: ignore[operator]
            case CompareOp.LE:
                return left <= right  # type: ignore[operator]
            case CompareOp.GT:
                return left > right  # type: ignore[operator]
            case _:
                return left >= right  # type: ignore[operator]

    def _contains(self, container: Value, item: Value) -> bool:
        if isinstance(container, list):
            return any(values_equal(item, element) for element in container)
        if isinstance(container, str):
            if not isinstance(item, str):
                raise self.fail(
                    f"'in' on a string needs a string on the left, got {type_name(item)}"
                )
            return item in container
        raise self.fail(
            f"'{self.op}' needs a list or string on the right, got {type_name(container)}"
        )


@dataclass(frozen=True)
class Call(Expr):
    name: str
    args: tuple[Expr, ...]

    def evaluate(self, context: EvalContext) -> Value:
        spec = context.functions.get(self.name)
        if spec is None:
            raise self.fail(f"unknown function '{self.name}'")
        if not spec.accepts(len(self.args)):
            raise self.fail(
                f"{self.name}() takes {spec.arity_text()} argument(s), got {len(self.args)}"
            )
        args = [arg.evaluate(context) for arg in self.args]
        try:
            return spec.impl(*args)
        except EvalError as error:
            if error.span is None:
                raise self.fail(error.message) from error
            raise
        except Exception as error:  # isolate faults in host-provided functions
            raise self.fail(f"{self.name}() failed: {error}") from error


# -- actions ---------------------------------------------------------------


@dataclass(frozen=True)
class Action(Node, ABC):
    @abstractmethod
    def execute(self, context: EvalContext) -> None: ...


@dataclass(frozen=True)
class SetAction(Action):
    """``set name = expr`` (or ``+=`` / ``-=``, where an unset name starts at 0)."""

    name: str
    op: AssignOp
    value: Expr

    def execute(self, context: EvalContext) -> None:
        value = self.value.evaluate(context)
        if self.op is not AssignOp.SET:
            current = context.results.get(self.name, Decimal(0))
            if not (is_number(current) and is_number(value)):
                raise self.fail(
                    f"'{self.op}' needs numbers, result.{self.name} is {type_name(current)} "
                    f"and the value is {type_name(value)}"
                )
            value = current + value if self.op is AssignOp.ADD else current - value  # type: ignore[operator]
        context.assign(self.name, value)


@dataclass(frozen=True)
class TagAction(Action):
    tag: str

    def execute(self, context: EvalContext) -> None:
        context.add_tag(self.tag)


@dataclass(frozen=True)
class StopAction(Action):
    """Halt the ruleset after this rule; lower-priority rules are not evaluated."""

    def execute(self, context: EvalContext) -> None:
        context.stop_requested = True


# -- top level -------------------------------------------------------------


@dataclass(frozen=True)
class Rule(Node):
    name: str
    priority: Decimal
    condition: Expr
    actions: tuple[Action, ...]
    # "#" comment lines directly above the rule; formatting metadata, not semantics.
    comments: tuple[str, ...] = field(default=(), compare=False, repr=False, kw_only=True)

    def matches(self, context: EvalContext) -> bool:
        return self.condition.evaluate_bool(context, "rule condition")

    def apply(self, context: EvalContext) -> None:
        for action in self.actions:
            action.execute(context)


@dataclass(frozen=True)
class RuleSet(Node):
    rules: tuple[Rule, ...]
    trailing_comments: tuple[str, ...] = field(default=(), compare=False, repr=False, kw_only=True)

    def in_execution_order(self) -> list[Rule]:
        """Highest priority first; ties keep source order (``sorted`` is stable)."""
        return sorted(self.rules, key=lambda rule: -rule.priority)
