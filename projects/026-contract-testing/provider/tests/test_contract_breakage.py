"""Demonstrates *why* contract tests exist, using two hypothetical provider changes.

Both changes wrap the real app in a tiny ASGI middleware that rewrites product
JSON on the way out, simulating a refactor that changed the wire format:

* renaming ``priceCents`` -> ``price`` breaks the storefront, and verification
  catches it before deploy;
* dropping ``warehouseLocation`` is safe, because no consumer asked for it.
  Consumer-driven contracts tell the provider which fields it is free to change.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

import pytest

from tests.verification import ContractViolation, build_provider, verify

pytestmark = pytest.mark.contract

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class RewriteProducts:
    """ASGI middleware applying ``transform`` to every product object in a response."""

    def __init__(self, app: ASGIApp, transform: Callable[[dict[str, Any]], None]) -> None:
        self._app = app
        self._transform = transform

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        start: Message = {}

        async def buffered_send(message: Message) -> None:
            nonlocal start
            if message["type"] == "http.response.start":
                start = message
                return
            body = self._rewrite(message.get("body", b""))
            headers = [(k, v) for k, v in start["headers"] if k != b"content-length"]
            headers.append((b"content-length", str(len(body)).encode()))
            await send({**start, "headers": headers})
            await send({"type": "http.response.body", "body": body})

        await self._app(scope, receive, buffered_send)

    def _rewrite(self, raw: bytes) -> bytes:
        try:
            payload = json.loads(raw)
        except ValueError:
            return raw
        products = payload.get("items", [payload]) if isinstance(payload, dict) else []
        for product in products:
            if isinstance(product, dict) and "priceCents" in product:
                self._transform(product)
        return json.dumps(payload).encode()


def rename_price(product: dict[str, Any]) -> None:
    product["price"] = product.pop("priceCents") / 100


def drop_warehouse(product: dict[str, Any]) -> None:
    product.pop("warehouseLocation", None)


def test_renaming_a_consumed_field_fails_verification() -> None:
    app, repo = build_provider()
    with pytest.raises(ContractViolation) as exc:
        verify(RewriteProducts(app, rename_price), repo)
    # The report names the exact field and every interaction that depends on it.
    assert "priceCents" in exc.value.report
    assert "a request for product P-100" in exc.value.report


def test_removing_an_unconsumed_field_still_verifies() -> None:
    app, repo = build_provider()
    verify(RewriteProducts(app, drop_warehouse), repo)
