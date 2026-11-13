"""The language's runtime value model and conversions at the JSON boundary.

Values are deliberately few: exact ``Decimal`` numbers (money must not drift),
strings, booleans, lists and ``null``. Nested objects exist only as facts that
paths navigate into. Python quirks are hidden here, e.g. ``True == 1`` is true
in Python but ``true == 1`` is false in the rules language.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

Value = Decimal | str | bool | list[Any] | dict[str, Any] | None


def type_name(value: object) -> str:
    """Language-level type name used in error messages."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, Decimal):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def is_number(value: object) -> bool:
    # bool is a subclass of int, never of Decimal, so an exact type check suffices.
    return type(value) is Decimal


def values_equal(left: object, right: object) -> bool:
    """Equality without Python's cross-type coercions (``True == Decimal(1)``)."""
    if type_name(left) != type_name(right):
        return False
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(map(values_equal, left, right))
    return left == right


def from_json(data: Any) -> Value:
    """Convert decoded JSON into language values. Floats go through ``str`` to stay exact."""
    if data is None or isinstance(data, (bool, str, Decimal)):
        return data
    if isinstance(data, (int, float)):
        return Decimal(str(data))
    if isinstance(data, list):
        return [from_json(item) for item in data]
    if isinstance(data, Mapping):
        return {str(key): from_json(value) for key, value in data.items()}
    raise TypeError(f"unsupported fact value of type {type(data).__name__}")


def to_json(value: Value) -> Any:
    """Convert a language value to JSON-safe data. Numbers become exact decimal strings."""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, list):
        return [to_json(item) for item in value]
    if isinstance(value, dict):
        return {key: to_json(item) for key, item in value.items()}
    return value


def display(value: Value) -> str:
    """Render a value as it would be written in rules source (used in traces)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, list):
        return "[" + ", ".join(display(item) for item in value) + "]"
    return "{...}"
