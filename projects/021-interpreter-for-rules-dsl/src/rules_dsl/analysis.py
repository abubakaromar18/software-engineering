"""Static checks run before any facts exist (``rules-dsl check``).

Business rules are often edited by people who cannot easily test them, so the
checker catches as much as it can without data:

* errors: duplicate rule names, unknown functions, wrong argument counts, and
  constant sub-expressions that are guaranteed to fail (``"a" - 1``, ``1 / 0``);
* warnings: conditions that are always true/false, rules made unreachable by an
  unconditional ``stop``, and reads of ``result.x`` before any rule assigns it.

The checker is conservative: a clean report means no *detectable* problem, not
that every rule succeeds on every input.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from .errors import EvalError
from .functions import FunctionRegistry
from .nodes import Call, Expr, Has, Literal, Node, Path, Rule, RuleSet, SetAction, StopAction
from .runtime import RESULT_ROOT, EvalContext
from .source import Source, Span
from .visitor import NodeVisitor, children, walk


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    severity: Severity
    message: str
    span: Span | None
    rule: str | None = None

    def render(self, source: Source | None = None) -> str:
        name = source.name if source else "<input>"
        where = f"{name}:{self.span}" if self.span else name
        context = f' (in rule "{self.rule}")' if self.rule else ""
        text = f"{where}: {self.severity}: {self.message}{context}"
        if source and self.span:
            text += "\n" + source.excerpt(self.span)
        return text


def is_constant(expr: Node) -> bool:
    """True when the value cannot depend on facts or (possibly impure) functions."""
    return not any(isinstance(node, (Path, Has, Call)) for node in walk(expr))


def result_reads(expr: Node) -> Iterable[Path]:
    """``result.x`` paths read by ``expr``. Reads inside ``has(...)`` are guards, not reads."""
    if isinstance(expr, Has):
        return
    if isinstance(expr, Path) and expr.parts[0] == RESULT_ROOT and len(expr.parts) > 1:
        yield expr
    for child in children(expr):
        yield from result_reads(child)


class _CallChecker(NodeVisitor):
    def __init__(self, functions: FunctionRegistry, report: _Reporter) -> None:
        self._functions = functions
        self._report = report

    def visit_Call(self, node: Call) -> None:
        spec = self._functions.get(node.name)
        if spec is None:
            known = ", ".join(spec.name for spec in self._functions)
            self._report.error(f"unknown function '{node.name}' (known: {known})", node.span)
        elif not spec.accepts(len(node.args)):
            self._report.error(
                f"{node.name}() takes {spec.arity_text()} argument(s), got {len(node.args)}",
                node.span,
            )
        self.generic_visit(node)


class _Reporter:
    def __init__(self) -> None:
        self.diagnostics: list[Diagnostic] = []
        self.rule: str | None = None

    def error(self, message: str, span: Span | None) -> None:
        self.diagnostics.append(Diagnostic(Severity.ERROR, message, span, self.rule))

    def warning(self, message: str, span: Span | None) -> None:
        self.diagnostics.append(Diagnostic(Severity.WARNING, message, span, self.rule))


class Checker:
    def __init__(self, functions: FunctionRegistry) -> None:
        self._functions = functions
        self._report = _Reporter()
        self._constant_context = EvalContext(facts={}, functions=functions)

    def check(self, ruleset: RuleSet) -> list[Diagnostic]:
        self._check_duplicates(ruleset)
        assigned_anywhere = {
            action.name
            for rule in ruleset.rules
            for action in rule.actions
            if isinstance(action, SetAction)
        }
        assigned_so_far: set[str] = set()
        stopped_by: Rule | None = None
        for rule in ruleset.in_execution_order():
            self._report.rule = rule.name
            if stopped_by is not None:
                self._report.warning(
                    f'unreachable: rule "{stopped_by.name}" always fires and stops', rule.span
                )
            _CallChecker(self._functions, self._report).visit(rule)
            for expr in self._expressions(rule):
                self._check_constants(expr)
            always = self._check_condition(rule)
            self._check_result_reads(rule, assigned_so_far, assigned_anywhere)
            if (
                always
                and stopped_by is None
                and any(isinstance(a, StopAction) for a in rule.actions)
            ):
                stopped_by = rule
        self._report.rule = None
        return sorted(
            self._report.diagnostics,
            key=lambda d: (d.span.start if d.span else -1, d.severity != Severity.ERROR),
        )

    # -- individual checks -------------------------------------------------

    def _check_duplicates(self, ruleset: RuleSet) -> None:
        seen: set[str] = set()
        for rule in ruleset.rules:
            if rule.name in seen:
                self._report.rule = rule.name
                self._report.error(f'duplicate rule name "{rule.name}"', rule.span)
            seen.add(rule.name)

    @staticmethod
    def _expressions(rule: Rule) -> list[Expr]:
        exprs = [rule.condition]
        exprs += [action.value for action in rule.actions if isinstance(action, SetAction)]
        return exprs

    def _check_constants(self, expr: Expr) -> None:
        """Evaluate each maximal fact-free sub-expression; failures are certain at run time."""
        if is_constant(expr):
            if not isinstance(expr, Literal):
                try:
                    expr.evaluate(self._constant_context)
                except EvalError as error:
                    self._report.error(f"always fails: {error.message}", error.span or expr.span)
            return
        for child in children(expr):
            if isinstance(child, Expr):
                self._check_constants(child)

    def _check_condition(self, rule: Rule) -> bool:
        """Warn about constant conditions; return True if the rule always fires."""
        if not is_constant(rule.condition):
            return False
        try:
            value = rule.condition.evaluate(self._constant_context)
        except EvalError:
            return False  # already reported by _check_constants
        if not isinstance(value, bool):
            self._report.error("condition is not a boolean", rule.condition.span)
            return False
        if not value:
            self._report.warning("condition is always false; rule never fires", rule.condition.span)
        elif not isinstance(rule.condition, Literal):
            self._report.warning("condition is always true", rule.condition.span)
        return value

    def _check_result_reads(
        self, rule: Rule, assigned_so_far: set[str], anywhere: set[str]
    ) -> None:
        def check(expr: Expr) -> None:
            for path in result_reads(expr):
                key = path.parts[1]
                if key not in anywhere:
                    self._report.warning(
                        f"'{path.dotted}' is never assigned by any rule", path.span
                    )
                elif key not in assigned_so_far:
                    self._report.warning(
                        f"'{path.dotted}' is read before any earlier rule assigns it", path.span
                    )

        check(rule.condition)
        for action in rule.actions:
            if isinstance(action, SetAction):
                check(action.value)
                assigned_so_far.add(action.name)


def check(ruleset: RuleSet, functions: FunctionRegistry) -> list[Diagnostic]:
    return Checker(functions).check(ruleset)
