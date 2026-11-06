# Offline targets use an empty package source, so they work without NuGet access.
OFFLINE_FEED := $(CURDIR)/.offline-feed
TESTS := tests/CatalogProxies.Tests

.PHONY: build test test-offline demo clean

build:
	dotnet build CatalogProxies.sln

test:            ## xUnit via dotnet test (needs NuGet)
	dotnet test CatalogProxies.sln

test-offline:    ## same tests, built against the bundled xUnit-compatible shim
	@mkdir -p $(OFFLINE_FEED)
	dotnet restore $(TESTS) -p:OfflineTests=true --source $(OFFLINE_FEED)
	dotnet build $(TESTS) -p:OfflineTests=true --no-restore
	dotnet $(TESTS)/bin/Debug/net8.0/CatalogProxies.Tests.dll

demo:
	@mkdir -p $(OFFLINE_FEED)
	dotnet restore samples/CatalogProxies.Demo --source $(OFFLINE_FEED)
	dotnet run --project samples/CatalogProxies.Demo --no-restore

clean:
	dotnet clean CatalogProxies.sln
	rm -rf $(OFFLINE_FEED)
