"""A small business-rules language built with the Interpreter pattern.

Typical use::

    engine = RuleEngine.from_source(rules_text)
    outcome = engine.evaluate({"order": {"total": 120}})
    outcome.results, outcome.tags, outcome.trace
"""

from .analysis import Diagnostic, Severity, check
from .engine import (
    EngineConfig,
    ErrorPolicy,
    InvalidRulesetError,
    Outcome,
    RuleEngine,
    RuleError,
    RuleStatus,
    TraceEntry,
)
from .errors import ConfigError, DslError, EvalError, LexError, ParseError, RulesetSyntaxError
from .formatter import format_expression, format_ruleset
from .functions import FunctionRegistry, FunctionSpec, builtin_functions
from .parser import parse, parse_expression
from .source import Source, Span

__all__ = [
    "ConfigError",
    "Diagnostic",
    "DslError",
    "EngineConfig",
    "ErrorPolicy",
    "EvalError",
    "FunctionRegistry",
    "FunctionSpec",
    "InvalidRulesetError",
    "LexError",
    "Outcome",
    "ParseError",
    "RulesetSyntaxError",
    "RuleEngine",
    "RuleError",
    "RuleStatus",
    "Severity",
    "Source",
    "Span",
    "TraceEntry",
    "builtin_functions",
    "check",
    "format_expression",
    "format_ruleset",
    "parse",
    "parse_expression",
]
