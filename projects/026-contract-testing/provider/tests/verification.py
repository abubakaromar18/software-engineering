"""Shared Pact verification routine used by the contract test modules.

Two contract sources are supported:

* **Local files** (default): ``../pacts/*.json``, written by the consumer's
  test run. Zero infrastructure - ideal for a monorepo like this one.
* **Pact Broker**: set ``PACT_BROKER_BASE_URL`` and verification pulls the
  contracts for the consumer's main branch *and* every deployed version, and
  (with ``PACT_PUBLISH_RESULTS=true``) publishes the outcome so that
  ``can-i-deploy`` can answer "is it safe to ship?".
"""

from __future__ import annotations

import os
from pathlib import Path

from pact import Verifier

from catalog_api.app import create_app
from catalog_api.repository import InMemoryCatalogRepository
from catalog_api.service import CatalogService
from tests.provider_states import build_state_handlers
from tests.support import SequentialIds, fixed_clock, running_server

PROVIDER_NAME = "catalog-api"
PACT_DIR = Path(__file__).resolve().parents[2] / "pacts"
VERIFIER_TOKEN = "verifier-token"

# Which consumer versions must this provider build stay compatible with?
CONSUMER_VERSION_SELECTORS = (
    '{"mainBranch": true}',
    '{"deployedOrReleased": true}',
)


class ContractViolation(AssertionError):
    """Raised when the provider does not satisfy a consumer contract.

    Carries the verifier's human-readable report so failures are actionable.
    """

    def __init__(self, report: str) -> None:
        super().__init__(f"provider does not satisfy consumer contracts:\n{report}")
        self.report = report


def build_provider() -> tuple[object, InMemoryCatalogRepository]:
    repo = InMemoryCatalogRepository()
    service = CatalogService(repo, clock=fixed_clock, id_generator=SequentialIds())
    return create_app(service, VERIFIER_TOKEN), repo


def broker_configured() -> bool:
    return bool(os.environ.get("PACT_BROKER_BASE_URL"))


def verify(
    app: object,
    repo: InMemoryCatalogRepository,
    *,
    use_broker: bool = False,
) -> Verifier:
    """Replay every consumer interaction against ``app``.

    Raises ``ContractViolation`` when any interaction does not match.

    The consumer records an *example* bearer token; real credentials belong to
    the provider, so the verifier overrides the header with one this test
    instance accepts. That is why 401 behaviour lives in test_api.py, not in
    the contract.
    """
    with running_server(app) as base_url:
        verifier = (
            Verifier(PROVIDER_NAME, host="127.0.0.1")
            .add_transport(url=base_url)
            .add_custom_header("Authorization", f"Bearer {VERIFIER_TOKEN}")
            .state_handler(build_state_handlers(repo), teardown=True)
            .set_error_on_empty_pact(enabled=True)
            .set_coloured_output(enabled=False)
        )
        if use_broker:
            _add_broker_source(verifier)
        else:
            verifier.add_source(PACT_DIR)
        try:
            return verifier.verify()
        except RuntimeError as exc:
            raise ContractViolation(verifier.output(strip_ansi=True)) from exc


def _add_broker_source(verifier: Verifier) -> None:
    (
        verifier.broker_source(os.environ["PACT_BROKER_BASE_URL"], selector=True)
        .consumer_versions(*CONSUMER_VERSION_SELECTORS)
        # New, not-yet-verified consumer expectations warn instead of failing
        # the provider build - consumers can't break the provider's pipeline.
        .include_pending()
        .build()
    )
    if os.environ.get("PACT_PUBLISH_RESULTS") == "true":
        verifier.set_publish_options(
            version=os.environ["PROVIDER_VERSION"],
            branch=os.environ.get("PROVIDER_BRANCH"),
        )
