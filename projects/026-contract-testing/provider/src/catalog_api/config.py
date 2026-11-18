"""Runtime configuration, read once from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Settings for the Catalog API process."""

    api_token: str
    host: str = "127.0.0.1"
    port: int = 8000

    @classmethod
    def from_env(cls) -> Settings:
        token = os.environ.get("CATALOG_API_TOKEN")
        if not token:
            raise RuntimeError(
                "CATALOG_API_TOKEN must be set (use any value for local development)"
            )
        return cls(
            api_token=token,
            host=os.environ.get("CATALOG_API_HOST", "127.0.0.1"),
            port=int(os.environ.get("CATALOG_API_PORT", "8000")),
        )
