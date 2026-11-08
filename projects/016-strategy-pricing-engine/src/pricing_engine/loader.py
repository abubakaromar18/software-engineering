"""Builds an engine and carts from plain data (typically parsed JSON).

Unknown keys are errors everywhere: a typo such as ``"categoris"`` would otherwise
silently widen a discount to the whole cart.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from . import rules as r
from .discounts import BuyXGetYFree, CategoryScoped, FixedAmountOff, PercentageOff, VolumeTiers
from .engine import PricingEngine
from .errors import ConfigError
from .models import Cart, LineItem
from .rules import Condition, Rule
from .stacking import BestForCustomer, Sequential, StackingPolicy
from .taxes import CategoryRateTax, FlatRateTax, NoTax


def to_decimal(value: Any) -> Decimal:
    """Accept str, int or Decimal. Floats are refused: 0.1 is not a price."""
    if isinstance(value, bool) or not isinstance(value, str | int | Decimal):
        raise ConfigError(f"expected a decimal string or integer, got {value!r}")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ConfigError(f"not a decimal number: {value!r}") from exc
    if not result.is_finite():
        raise ConfigError(f"number must be finite, got {value!r}")
    return result


def to_date(value: Any) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"expected an ISO date, got {value!r}") from exc


def _to_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"expected an integer, got {value!r}")
    return value


class StrategyRegistry:
    """Maps a config ``type`` to a factory: the extension point for new strategies."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[..., Any]] = {}

    def register(self, type_name: str, factory: Callable[..., Any]) -> None:
        if type_name in self._factories:
            raise ConfigError(f"strategy type {type_name!r} is already registered")
        self._factories[type_name] = factory

    def build(self, spec: Any) -> Any:
        if not isinstance(spec, Mapping) or "type" not in spec:
            raise ConfigError(f"strategy needs a 'type': {spec!r}")
        params = {key: value for key, value in spec.items() if key != "type"}
        type_name = spec["type"]
        if type_name not in self._factories:
            raise ConfigError(f"unknown strategy type {type_name!r}")
        factory = self._factories[type_name]
        # Bind first so only bad config, not a TypeError inside the factory, is reported here.
        try:
            inspect.signature(factory).bind(**params)
        except TypeError as exc:
            raise ConfigError(f"strategy {type_name!r}: {exc}") from exc
        return factory(**params)


def default_discount_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    registry.register("percentage", lambda percent: PercentageOff(to_decimal(percent)))
    registry.register("fixed", lambda amount: FixedAmountOff(to_decimal(amount)))
    registry.register(
        "buy_x_get_y",
        lambda buy, free: BuyXGetYFree(_to_int(buy), _to_int(free)),
    )
    registry.register(
        "volume",
        lambda tiers: VolumeTiers(
            tuple((_to_int(t["min_quantity"]), to_decimal(t["percent"])) for t in tiers)
        ),
    )
    return registry


def default_tax_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    registry.register("none", NoTax)
    registry.register("flat", lambda rate: FlatRateTax(to_decimal(rate)))
    registry.register(
        "category_rate",
        lambda default, rates: CategoryRateTax(
            to_decimal(default), {k: to_decimal(v) for k, v in rates.items()}
        ),
    )
    return registry


def _names(value: Any) -> tuple[str, ...]:
    return (value,) if isinstance(value, str) else tuple(value)


def _between(value: Any) -> Condition:
    if not isinstance(value, list) or len(value) != 2:
        raise ConfigError(f"'between' needs [start, end], got {value!r}")
    start, end = to_date(value[0]), to_date(value[1])
    if start > end:
        raise ConfigError(f"'between' start {start} is after end {end}")
    return r.date_between(start, end)


_LEAF_CONDITIONS: dict[str, Callable[[Any], Condition]] = {
    "tier": lambda v: r.tier_in(*_names(v)),
    "region": lambda v: r.region_in(*_names(v)),
    "coupon": r.has_coupon,
    "min_subtotal": lambda v: r.min_subtotal(to_decimal(v)),
    "between": _between,
}


def parse_condition(spec: Any) -> Condition:
    """Parse e.g. ``{"all": [{"tier": "gold"}, {"not": {"region": "EU"}}]}``."""
    if not isinstance(spec, Mapping) or len(spec) != 1:
        raise ConfigError(f"condition must be an object with exactly one key: {spec!r}")
    key, value = next(iter(spec.items()))
    if key == "all":
        return r.all_of(*(parse_condition(item) for item in value))
    if key == "any":
        return r.any_of(*(parse_condition(item) for item in value))
    if key == "not":
        return r.negate(parse_condition(value))
    if key not in _LEAF_CONDITIONS:
        raise ConfigError(f"unknown condition {key!r}")
    return _LEAF_CONDITIONS[key](value)


def _require_keys(data: Any, required: set[str], optional: set[str], what: str) -> None:
    if not isinstance(data, Mapping):
        raise ConfigError(f"{what} must be an object, got {data!r}")
    missing = required - data.keys()
    unknown = data.keys() - required - optional
    if missing:
        raise ConfigError(f"{what} is missing {sorted(missing)}")
    if unknown:
        raise ConfigError(f"{what} has unknown keys {sorted(unknown)}")


def _require_list(value: Any, what: str) -> None:
    if not isinstance(value, list):
        raise ConfigError(f"{what} must be a list, got {value!r}")


def _build_discount(spec: Any, registry: StrategyRegistry) -> Any:
    """``categories`` works on any discount type, including custom ones."""
    if not isinstance(spec, Mapping) or "categories" not in spec:
        return registry.build(spec)
    inner = registry.build({k: v for k, v in spec.items() if k != "categories"})
    return CategoryScoped(inner, frozenset(_names(spec["categories"])))


def _build_rules(specs: Any, build_strategy: Callable[[Any], Any], kind: str) -> list[Rule[Any]]:
    _require_list(specs, f"{kind} rules")
    built: list[Rule[Any]] = []
    seen: set[str] = set()
    for spec in specs:
        _require_keys(spec, {"name", "strategy"}, {"when", "priority"}, f"{kind} rule")
        name = spec["name"]
        if name in seen:
            raise ConfigError(f"duplicate {kind} rule name {name!r}")
        seen.add(name)
        try:
            when = parse_condition(spec["when"]) if "when" in spec else r.always
            strategy = build_strategy(spec["strategy"])
            priority = _to_int(spec.get("priority", 100))
        except (KeyError, TypeError, AttributeError) as exc:
            raise ConfigError(f"{kind} rule {name!r}: malformed definition: {exc!r}") from exc
        except ConfigError as exc:
            raise ConfigError(f"{kind} rule {name!r}: {exc}") from exc
        built.append(Rule(name=name, when=when, strategy=strategy, priority=priority))
    return built


_STACKING: dict[str, Callable[[], StackingPolicy]] = {
    "sequential": Sequential,
    "best": BestForCustomer,
}


def engine_from_config(
    config: Any,
    discount_registry: StrategyRegistry | None = None,
    tax_registry: StrategyRegistry | None = None,
) -> PricingEngine:
    _require_keys(config, {"taxes"}, {"discounts", "stacking"}, "config")
    discounts = discount_registry or default_discount_registry()
    taxes = tax_registry or default_tax_registry()
    stacking = config.get("stacking", "sequential")
    if not isinstance(stacking, str) or stacking not in _STACKING:
        raise ConfigError(f"unknown stacking policy {stacking!r}")
    return PricingEngine(
        discount_rules=_build_rules(
            config.get("discounts", []), lambda s: _build_discount(s, discounts), "discount"
        ),
        tax_rules=_build_rules(config["taxes"], taxes.build, "tax"),
        stacking=_STACKING[stacking](),
    )


def _line_item_from_dict(data: Any) -> LineItem:
    _require_keys(data, {"sku", "category", "unit_price", "quantity"}, set(), "item")
    return LineItem(
        sku=data["sku"],
        category=data["category"],
        unit_price=to_decimal(data["unit_price"]),
        quantity=data["quantity"],
    )


def cart_from_dict(data: Any) -> Cart:
    _require_keys(
        data, {"items", "order_date"}, {"region", "customer_tier", "coupons"}, "cart"
    )
    _require_list(data["items"], "cart items")
    _require_list(data.get("coupons", []), "cart coupons")
    return Cart(
        items=tuple(_line_item_from_dict(item) for item in data["items"]),
        order_date=to_date(data["order_date"]),
        region=data.get("region", ""),
        customer_tier=data.get("customer_tier", "standard"),
        coupons=frozenset(data.get("coupons", [])),
    )
