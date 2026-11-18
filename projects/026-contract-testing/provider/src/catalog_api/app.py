"""HTTP adapter: FastAPI routes that translate between the wire and the service."""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from catalog_api.errors import CatalogError
from catalog_api.schemas import (
    ErrorBody,
    ErrorOut,
    OrderIn,
    OrderOut,
    ProductListOut,
    ProductOut,
)
from catalog_api.service import CatalogService, OrderRequestLine


class _Unauthorized(Exception):
    """Raised by the auth dependency; rendered as a 401 error body."""


def _error(status: int, code: str, message: str) -> JSONResponse:
    body = ErrorOut(error=ErrorBody(code=code, message=message))
    return JSONResponse(status_code=status, content=body.model_dump(by_alias=True))


def create_app(service: CatalogService, api_token: str) -> FastAPI:
    """Build the ASGI app. All collaborators are passed in - no globals."""
    app = FastAPI(title="Catalog API", version="1.0.0")

    def require_token(
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        scheme, _, token = (authorization or "").partition(" ")
        # Constant-time comparison avoids leaking the token via timing.
        if scheme != "Bearer" or not hmac.compare_digest(token, api_token):
            raise _Unauthorized

    @app.exception_handler(CatalogError)
    async def _catalog_error(_: Request, exc: CatalogError) -> JSONResponse:
        return _error(exc.status_code, exc.code, exc.message)

    @app.exception_handler(_Unauthorized)
    async def _unauthorized(_: Request, __: _Unauthorized) -> JSONResponse:
        return _error(401, "UNAUTHORIZED", "A valid bearer token is required")

    @app.exception_handler(RequestValidationError)
    async def _bad_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0]
        where = ".".join(str(part) for part in first["loc"])
        return _error(422, "INVALID_REQUEST", f"{where}: {first['msg']}")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    authed = [Depends(require_token)]

    @app.get("/products/{product_id}", dependencies=authed)
    def get_product(product_id: str) -> ProductOut:
        return ProductOut.from_domain(service.get_product(product_id))

    @app.get("/products", dependencies=authed)
    def list_products(category: str | None = None) -> ProductListOut:
        items = [ProductOut.from_domain(p) for p in service.list_products(category)]
        return ProductListOut(items=items, count=len(items))

    @app.post("/orders", status_code=201, dependencies=authed)
    def place_order(payload: OrderIn) -> OrderOut:
        lines = [OrderRequestLine(i.product_id, i.quantity) for i in payload.items]
        return OrderOut.from_domain(service.place_order(lines))

    return app
