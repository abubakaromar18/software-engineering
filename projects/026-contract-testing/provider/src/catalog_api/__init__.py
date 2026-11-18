"""Catalog API: a small product catalog and ordering service.

This package is the *provider* in a consumer-driven contract relationship with
the JavaScript storefront client in ``../consumer``.
"""

from catalog_api.app import create_app

__all__ = ["create_app"]
