"""HTTP-level tests for behaviour the contract deliberately does not cover.

Pact pins the shapes the storefront relies on; these tests cover the rest of
the provider's surface (auth failures, validation, health).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from catalog_api.repository import InMemoryCatalogRepository
from tests.conftest import make_product


def test_health_is_public(client: TestClient) -> None:
    client.headers.pop("Authorization")
    assert client.get("/health").json() == {"status": "ok"}


def test_missing_or_wrong_token_is_rejected(client: TestClient) -> None:
    for header in (None, "Bearer wrong", "Basic unit-test-token"):
        headers = {"Authorization": header} if header else {}
        client.headers.pop("Authorization", None)
        response = client.get("/products/P-100", headers=headers)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_product_is_serialised_in_camel_case(
    client: TestClient, repo: InMemoryCatalogRepository
) -> None:
    repo.save_product(make_product(stock=0))
    body = client.get("/products/P-100").json()
    assert body["priceCents"] == 4599
    assert body["inStock"] is False
    assert "price_cents" not in body


def test_unknown_product_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/products/P-404")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "NOT_FOUND", "message": "Product P-404 does not exist"}
    }


def test_malformed_order_body_is_422(client: TestClient) -> None:
    response = client.post("/orders", json={"items": [{"productId": "P-1"}]})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_order_round_trip(client: TestClient, repo: InMemoryCatalogRepository) -> None:
    repo.save_product(make_product(stock=3))
    response = client.post("/orders", json={"items": [{"productId": "P-100", "quantity": 2}]})
    assert response.status_code == 201
    body = response.json()
    assert body["totalCents"] == 9198
    assert body["createdAt"] == "2026-11-18T15:30:00Z"
    assert body["items"] == [{"productId": "P-100", "quantity": 2, "unitPriceCents": 4599}]
