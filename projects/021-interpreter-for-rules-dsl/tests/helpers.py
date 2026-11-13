"""Shared test helpers (importable as ``helpers`` via the pytest pythonpath)."""

from __future__ import annotations

from typing import Any

from rules_dsl import builtin_functions, parse_expression
from rules_dsl.runtime import EvalContext
from rules_dsl.values import Value, from_json


def evaluate(expr: str, facts: dict[str, Any] | None = None) -> Value:
    """Parse and evaluate a single expression against JSON-style facts."""
    context = EvalContext(facts=from_json(facts or {}), functions=builtin_functions())
    return parse_expression(expr).evaluate(context)
