"""Configuration, loaded from the environment rather than hard-coded."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from shipping_facade.errors import ValidationError


@dataclass(frozen=True, slots=True)
class ShippingConfig:
    account: str
    api_key: str
    environment: str = "SANDBOX"
    max_attempts: int = 3
    backoff_seconds: float = 0.2

    def __post_init__(self) -> None:
        if not self.account or not self.api_key:
            raise ValidationError("account and api_key are required")
        if self.environment not in ("SANDBOX", "PROD"):
            raise ValidationError(f"environment must be SANDBOX or PROD, got {self.environment!r}")
        if self.max_attempts < 1:
            raise ValidationError("max_attempts must be at least 1")
        if self.backoff_seconds < 0:
            raise ValidationError("backoff_seconds must not be negative")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ShippingConfig:
        """Build a config from ``ACME_*`` variables (``os.environ`` by default)."""
        env = os.environ if env is None else env
        try:
            return cls(
                account=env.get("ACME_ACCOUNT", ""),
                api_key=env.get("ACME_API_KEY", ""),
                environment=env.get("ACME_ENV", "SANDBOX"),
                max_attempts=int(env.get("ACME_MAX_ATTEMPTS", "3")),
                backoff_seconds=float(env.get("ACME_BACKOFF_SECONDS", "0.2")),
            )
        except ValueError as exc:
            raise ValidationError(f"invalid numeric setting: {exc}") from exc
