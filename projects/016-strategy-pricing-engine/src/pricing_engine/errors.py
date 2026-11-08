"""Exception hierarchy: callers can catch ``PricingError`` for anything raised here."""


class PricingError(Exception):
    """Base class for every error raised by the engine."""


class InvalidCartError(PricingError, ValueError):
    """The cart or one of its line items is malformed."""


class ConfigError(PricingError, ValueError):
    """A rule, condition or strategy definition is invalid."""


class StrategyError(PricingError):
    """A strategy broke its contract, e.g. returned a negative amount."""


class NoTaxRuleError(PricingError):
    """No tax rule matched. Pricing fails closed rather than silently charging no tax."""
