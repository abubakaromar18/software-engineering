from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from catalog_api.app import create_app
from catalog_api.models import Product
from catalog_api.repository import InMemoryCatalogRepository
from catalog_api.service import CatalogService
from tests.support import SequentialIds, fixed_clock

TOKEN = "unit-test-token"


def make_product(**overrides: object) -> Product:
    fields: dict[str, object] = {
        "id": "P-100",
        "name": "Designing Data-Intensive Applications",
        "category": "books",
        "price_cents": 4599,
        "currency": "USD",
        "stock": 10,
        "tags": ["databases"],
    }
    fields.update(overrides)
    return Product(**fields)  # type: ignore[arg-type]


@pytest.fixture
def repo() -> InMemoryCatalogRepository:
    return InMemoryCatalogRepository()


@pytest.fixture
def service(repo: InMemoryCatalogRepository) -> CatalogService:
    return CatalogService(repo, clock=fixed_clock, id_generator=SequentialIds())


@pytest.fixture
def client(service: CatalogService) -> TestClient:
    return TestClient(create_app(service, TOKEN), headers={"Authorization": f"Bearer {TOKEN}"})
