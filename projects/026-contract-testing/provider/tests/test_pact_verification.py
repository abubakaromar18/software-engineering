"""Provider verification: does this build of catalog-api honour its consumers?

In CI this is the gate that runs on every provider change. Locally it reads the
pact file the JS consumer committed to ``../pacts``; when ``PACT_BROKER_BASE_URL``
is set it pulls contracts from the broker instead (see the README).
"""

from __future__ import annotations

import pytest

from tests.verification import PACT_DIR, broker_configured, build_provider, verify

pytestmark = pytest.mark.contract


@pytest.mark.skipif(broker_configured(), reason="contracts come from the Pact Broker")
def test_pact_files_are_present() -> None:
    assert list(PACT_DIR.glob("*-catalog-api.json")), (
        "no pacts found - run `npm test` in ../consumer first"
    )


def test_provider_honours_all_consumer_contracts() -> None:
    app, repo = build_provider()
    verify(app, repo, use_broker=broker_configured())
