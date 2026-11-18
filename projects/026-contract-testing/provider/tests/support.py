"""Test helpers: deterministic collaborators and a real HTTP server on a free port."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import uvicorn

FIXED_NOW = datetime(2026, 11, 18, 15, 30, 0, tzinfo=UTC)


def fixed_clock() -> datetime:
    return FIXED_NOW


class SequentialIds:
    """Order ids that match the production format (ORD- + 8 hex chars)."""

    def __init__(self) -> None:
        self._n = 0

    def __call__(self) -> str:
        self._n += 1
        return f"ORD-{self._n:08X}"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def running_server(app: object) -> Iterator[str]:
    """Serve an ASGI app with uvicorn in a background thread; yield its base URL."""
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline or not thread.is_alive():
            raise RuntimeError("uvicorn did not start")
        time.sleep(0.02)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
