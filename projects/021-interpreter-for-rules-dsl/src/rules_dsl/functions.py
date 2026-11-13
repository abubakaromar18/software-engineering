"""Function registry: the language's extension point.

Functions receive already-evaluated arguments. Arity is declared up front so the
static checker can reject ``round(1, 2, 3)`` before any facts exist. Host
applications add domain functions with :meth:`FunctionRegistry.register`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .errors import ConfigError, EvalError
from .values import Value, is_number, type_name

Impl = Callable[..., Value]


@dataclass(frozen=True, slots=True)
class FunctionSpec:
    name: str
    impl: Impl
    min_args: int
    max_args: int | None  # None means variadic
    doc: str = ""

    def accepts(self, count: int) -> bool:
        return count >= self.min_args and (self.max_args is None or count <= self.max_args)

    def arity_text(self) -> str:
        if self.max_args is None:
            return f"at least {self.min_args}"
        if self.min_args == self.max_args:
            return str(self.min_args)
        return f"{self.min_args} to {self.max_args}"


class FunctionRegistry:
    def __init__(self, specs: Sequence[FunctionSpec] = ()) -> None:
        self._specs: dict[str, FunctionSpec] = {}
        for spec in specs:
            self.add(spec)

    def add(self, spec: FunctionSpec) -> None:
        if not spec.name.isidentifier():
            raise ConfigError(f"invalid function name {spec.name!r}")
        if spec.name in self._specs:
            raise ConfigError(f"function {spec.name!r} is already registered")
        self._specs[spec.name] = spec

    def register(
        self, name: str, min_args: int, max_args: int | None = None, doc: str = ""
    ) -> Callable[[Impl], Impl]:
        """Decorator form: ``@registry.register("vat", 1, 1)``."""

        def decorate(impl: Impl) -> Impl:
            self.add(FunctionSpec(name, impl, min_args, max_args, doc))
            return impl

        return decorate

    def get(self, name: str) -> FunctionSpec | None:
        return self._specs.get(name)

    def copy(self) -> FunctionRegistry:
        return FunctionRegistry(list(self._specs.values()))

    def __iter__(self) -> Iterator[FunctionSpec]:
        return iter(sorted(self._specs.values(), key=lambda spec: spec.name))

    def __contains__(self, name: object) -> bool:
        return name in self._specs


# -- built-ins -------------------------------------------------------------


def _require(value: Value, expected: str, function: str, position: int) -> None:
    actual = type_name(value)
    if actual != expected:
        raise EvalError(f"{function}() argument {position} must be a {expected}, got {actual}")


def _numbers(function: str, args: tuple[Value, ...]) -> list[Decimal]:
    """Accept either ``f(a, b, c)`` or ``f([a, b, c])``."""
    items = list(args[0]) if len(args) == 1 and isinstance(args[0], list) else list(args)
    if not items:
        raise EvalError(f"{function}() of an empty list")
    for position, item in enumerate(items, start=1):
        _require(item, "number", function, position)
    return items  # type: ignore[return-value]


def _len(value: Value) -> Decimal:
    if not isinstance(value, (str, list)):
        raise EvalError(f"len() needs a string or list, got {type_name(value)}")
    return Decimal(len(value))


def _abs(value: Value) -> Decimal:
    _require(value, "number", "abs", 1)
    return abs(value)  # type: ignore[arg-type]


def _round(value: Value, places: Value = Decimal(0)) -> Decimal:
    _require(value, "number", "round", 1)
    _require(places, "number", "round", 2)
    if places != places.to_integral_value() or places < 0:  # type: ignore[union-attr,operator]
        raise EvalError("round() places must be a non-negative whole number")
    quantum = Decimal(1).scaleb(-int(places))  # type: ignore[arg-type]
    return value.quantize(quantum, rounding=ROUND_HALF_UP)  # type: ignore[union-attr]


def _lower(value: Value) -> str:
    _require(value, "string", "lower", 1)
    return value.lower()  # type: ignore[union-attr]


def _upper(value: Value) -> str:
    _require(value, "string", "upper", 1)
    return value.upper()  # type: ignore[union-attr]


def _starts_with(value: Value, prefix: Value) -> bool:
    _require(value, "string", "starts_with", 1)
    _require(prefix, "string", "starts_with", 2)
    return value.startswith(prefix)  # type: ignore[union-attr,arg-type]


def _sum(values: Value) -> Decimal:
    _require(values, "list", "sum", 1)
    total = Decimal(0)
    for position, item in enumerate(values, start=1):  # type: ignore[arg-type]
        if not is_number(item):
            raise EvalError(f"sum() item {position} must be a number, got {type_name(item)}")
        total += item
    return total


def builtin_functions() -> FunctionRegistry:
    """A fresh registry holding the standard library. Callers may extend their copy."""
    return FunctionRegistry(
        [
            FunctionSpec("len", _len, 1, 1, "length of a string or list"),
            FunctionSpec("min", lambda *a: min(_numbers("min", a)), 1, None, "smallest number"),
            FunctionSpec("max", lambda *a: max(_numbers("max", a)), 1, None, "largest number"),
            FunctionSpec("abs", _abs, 1, 1, "absolute value"),
            FunctionSpec("round", _round, 1, 2, "round half up to N places (default 0)"),
            FunctionSpec("lower", _lower, 1, 1, "lower-case a string"),
            FunctionSpec("upper", _upper, 1, 1, "upper-case a string"),
            FunctionSpec("starts_with", _starts_with, 2, 2, "string prefix test"),
            FunctionSpec("sum", _sum, 1, 1, "sum of a list of numbers"),
        ]
    )
