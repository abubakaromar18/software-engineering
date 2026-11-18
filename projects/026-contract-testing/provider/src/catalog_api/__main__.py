"""Run the API locally: ``CATALOG_API_TOKEN=dev python -m catalog_api``."""

from __future__ import annotations

import uvicorn

from catalog_api.app import create_app
from catalog_api.config import Settings
from catalog_api.repository import InMemoryCatalogRepository, demo_products
from catalog_api.service import CatalogService


def main() -> None:
    settings = Settings.from_env()
    service = CatalogService(InMemoryCatalogRepository(demo_products()))
    uvicorn.run(create_app(service, settings.api_token), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
