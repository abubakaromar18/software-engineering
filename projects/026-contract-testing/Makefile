# Consumer-driven contract testing: storefront (JS) -> catalog-api (Python).
#
# The order matters: the consumer's tests *produce* the contract, the
# provider's tests *verify* it. `make contract` runs both, in order.

PYTHON      ?= python3
VENV        := provider/.venv
PY          := $(VENV)/bin/python
VERSION     ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)
BRANCH      ?= $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)
BROKER_URL  ?= http://localhost:9292
PACT_CLI    := docker run --rm --network host -v $(CURDIR)/pacts:/pacts pactfoundation/pact-cli:latest

.PHONY: install test contract test-consumer test-provider lint demo \
        broker-up broker-down publish verify-broker can-i-deploy clean

install: consumer/node_modules $(VENV)

consumer/node_modules: consumer/package.json
	cd consumer && npm install
	@touch $@

$(VENV): provider/pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install -q -e 'provider[test]'
	@touch $@

test: contract

contract: test-consumer test-provider

test-consumer: consumer/node_modules
	cd consumer && npm test

test-provider: $(VENV)
	cd provider && .venv/bin/pytest -q

lint: $(VENV)
	cd provider && .venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests

demo: install
	@cd provider && CATALOG_API_TOKEN=dev-token .venv/bin/python -m catalog_api & \
	  server=$$!; trap "kill $$server" EXIT; sleep 2; \
	  cd consumer && CATALOG_API_TOKEN=dev-token npm run -s demo

# --- Pact Broker workflow (requires Docker) ---------------------------------

broker-up:
	docker compose up -d --wait

broker-down:
	docker compose down -v

publish: test-consumer
	$(PACT_CLI) pact-broker publish /pacts \
	  --consumer-app-version $(VERSION) --branch $(BRANCH) --broker-base-url $(BROKER_URL)

verify-broker: $(VENV)
	cd provider && PACT_BROKER_BASE_URL=$(BROKER_URL) PACT_PUBLISH_RESULTS=true \
	  PROVIDER_VERSION=$(VERSION) PROVIDER_BRANCH=$(BRANCH) .venv/bin/pytest -q -m contract

can-i-deploy:
	$(PACT_CLI) pact-broker can-i-deploy --pacticipant storefront --version $(VERSION) \
	  --to-environment production --broker-base-url $(BROKER_URL)

clean:
	rm -rf consumer/node_modules $(VENV) provider/.pytest_cache
