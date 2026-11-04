"""The only module that talks to the vendor client.

It owns the vendor's operational quirks so the facade does not have to:
lazy connection, transparent reconnect when a session expires, bounded retry
with exponential backoff on ``503``, and turning return codes into exceptions.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from acme_ship_sdk import AcmeShipClient
from acme_ship_sdk.client import (
    RC_BAD_REQUEST,
    RC_BUSY,
    RC_CONFLICT,
    RC_NOT_FOUND,
    RC_OK,
    RC_SESSION_EXPIRED,
    RC_UNAUTHORIZED,
)
from shipping_facade.config import ShippingConfig
from shipping_facade.errors import (
    AuthenticationError,
    CancellationRejectedError,
    InvalidShipmentError,
    ProviderUnavailableError,
    ShipmentNotFoundError,
    ShippingError,
)

log = logging.getLogger(__name__)

_ERRORS_BY_CODE: dict[int, type[ShippingError]] = {
    RC_BAD_REQUEST: InvalidShipmentError,
    RC_UNAUTHORIZED: AuthenticationError,
    RC_NOT_FOUND: ShipmentNotFoundError,
    RC_CONFLICT: CancellationRejectedError,
}


class VendorGateway:
    def __init__(
        self,
        client: AcmeShipClient,
        config: ShippingConfig,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self._config = config
        self._sleep = sleep  # injected so tests do not actually wait
        self._connected = False

    def call(self, operation: str, request: Callable[[AcmeShipClient], dict]) -> dict:
        """Run ``request`` until it succeeds, fails for good, or retries run out.

        ``request`` receives the vendor client and must return a vendor-style
        dict with an ``rc`` key, so callers never hold the client themselves.
        """
        for attempt in range(1, self._config.max_attempts + 1):
            response = self._send(operation, request)
            rc = response.get("rc")
            if rc == RC_OK:
                return response
            if rc != RC_BUSY:
                raise self._to_error(operation, response)
            if attempt < self._config.max_attempts:
                delay = self._config.backoff_seconds * 2 ** (attempt - 1)
                log.warning("%s: vendor busy (attempt %d), retrying in %.2fs", operation, attempt, delay)
                self._sleep(delay)
        raise ProviderUnavailableError(
            f"{operation}: vendor unavailable after {self._config.max_attempts} attempts",
            vendor_code=RC_BUSY,
        )

    def _send(self, operation: str, request: Callable[[AcmeShipClient], dict]) -> dict:
        """One attempt. An expired session is not a failure: reconnect and resend
        once, without spending one of the caller's retry attempts."""
        self._ensure_connected()
        response = request(self._client)
        if response.get("rc") == RC_SESSION_EXPIRED:
            log.info("%s: session expired, reconnecting", operation)
            self._connected = False
            self._ensure_connected()
            response = request(self._client)
        return response

    def _ensure_connected(self) -> None:
        if self._connected:
            return
        rc = self._client.Connect(self._config.account, self._config.api_key, self._config.environment)
        if rc != RC_OK:
            raise AuthenticationError("vendor refused the configured credentials", vendor_code=rc)
        self._connected = True

    @staticmethod
    def _to_error(operation: str, response: dict) -> ShippingError:
        rc = response.get("rc")
        message = str(response.get("msg", "no message")).capitalize()
        error_type = _ERRORS_BY_CODE.get(rc, ShippingError)
        return error_type(f"{operation}: {message}", vendor_code=rc)
