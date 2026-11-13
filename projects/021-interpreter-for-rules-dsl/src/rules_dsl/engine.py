"""The rule engine: the client of the Interpreter pattern.

Execution model, chosen for predictability over expressiveness:

* single pass, highest ``priority`` first, ties in source order;
* each matching rule's actions run as a transaction (all or nothing);
* later rules see earlier results through ``result.<name>``;
* ``stop`` ends the pass; skipped rules are reported as ``not reached``.

Every run returns a full trace, so "why did this order get free shipping?" can
be answered from the output alone.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .analysis import Diagnostic, Severity, check
from .errors import ConfigError, DslError, EvalError
from .functions import FunctionRegistry, builtin_functions
from .nodes import RuleSet
from .parser import parse
from .runtime import RESULT_ROOT, Change, EvalContext
from .source import Source
from .values import Value, from_json, to_json


class ErrorPolicy(StrEnum):
    RAISE = "raise"  # a failing rule aborts the whole evaluation
    SKIP = "skip"  # a failing rule is rolled back, recorded in the trace, and skipped


class RuleStatus(StrEnum):
    FIRED = "fired"
    NOT_MATCHED = "not matched"
    FAILED = "failed"
    NOT_REACHED = "not reached"


@dataclass(frozen=True, slots=True)
class EngineConfig:
    on_error: ErrorPolicy = ErrorPolicy.RAISE


class RuleError(EvalError):
    """An :class:`EvalError` annotated with the rule it happened in."""

    def __init__(self, rule: str, cause: EvalError) -> None:
        super().__init__(f'in rule "{rule}": {cause.message}', cause.span)
        self.rule = rule
        self.cause = cause


class InvalidRulesetError(DslError):
    """Static checking found errors; nothing was evaluated."""

    kind = "invalid ruleset"

    def __init__(self, diagnostics: list[Diagnostic]) -> None:
        errors = [d for d in diagnostics if d.severity is Severity.ERROR]
        super().__init__(f"{len(errors)} error(s) found by the checker")
        self.diagnostics = diagnostics

    def render(self, source: Source | None = None) -> str:
        return "\n".join(d.render(source) for d in self.diagnostics)


@dataclass(frozen=True, slots=True)
class TraceEntry:
    rule: str
    status: RuleStatus
    changes: tuple[Change, ...] = ()
    error: EvalError | None = None


@dataclass
class Outcome:
    results: dict[str, Value]
    tags: list[str]
    trace: list[TraceEntry] = field(default_factory=list)

    @property
    def fired(self) -> list[str]:
        return [entry.rule for entry in self.trace if entry.status is RuleStatus.FIRED]

    def to_json(self) -> dict[str, Any]:
        return {"results": to_json(self.results), "tags": self.tags, "fired": self.fired}


class RuleEngine:
    def __init__(
        self,
        ruleset: RuleSet,
        functions: FunctionRegistry | None = None,
        config: EngineConfig | None = None,
    ) -> None:
        self.ruleset = ruleset
        self.functions = functions if functions is not None else builtin_functions()
        self.config = config or EngineConfig()
        self._order = ruleset.in_execution_order()

    @classmethod
    def from_source(
        cls,
        text: str | Source,
        functions: FunctionRegistry | None = None,
        config: EngineConfig | None = None,
    ) -> RuleEngine:
        """Parse and statically check; refuse to build an engine from a broken ruleset."""
        functions = functions if functions is not None else builtin_functions()
        ruleset = parse(text)
        diagnostics = check(ruleset, functions)
        if any(d.severity is Severity.ERROR for d in diagnostics):
            raise InvalidRulesetError(diagnostics)
        return cls(ruleset, functions, config)

    def evaluate(self, facts: Mapping[str, Any]) -> Outcome:
        context = EvalContext(facts=self._prepare(facts), functions=self.functions)
        trace: list[TraceEntry] = []
        stopped = False
        for rule in self._order:
            if stopped:
                trace.append(TraceEntry(rule.name, RuleStatus.NOT_REACHED))
                continue
            context.begin()
            try:
                if not rule.matches(context):
                    trace.append(TraceEntry(rule.name, RuleStatus.NOT_MATCHED))
                    continue
                rule.apply(context)
            except EvalError as error:
                context.rollback()
                if self.config.on_error is ErrorPolicy.RAISE:
                    raise RuleError(rule.name, error) from error
                trace.append(TraceEntry(rule.name, RuleStatus.FAILED, error=error))
                continue
            changes, stopped = context.commit()
            trace.append(TraceEntry(rule.name, RuleStatus.FIRED, tuple(changes)))
        return Outcome(dict(context.results), context.tags, trace)

    @staticmethod
    def _prepare(facts: Mapping[str, Any]) -> dict[str, Value]:
        if not isinstance(facts, Mapping):
            raise ConfigError(f"facts must be an object, got {type(facts).__name__}")
        if RESULT_ROOT in facts:
            raise ConfigError(f"'{RESULT_ROOT}' is reserved for rule outputs; rename that fact")
        try:
            converted = from_json(facts)
        except TypeError as error:
            raise ConfigError(str(error)) from error
        return converted  # type: ignore[return-value]
