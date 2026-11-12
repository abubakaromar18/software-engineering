#!/usr/bin/env bash
# Runs the test suite. Prefers the real xUnit project (`dotnet test`); if NuGet
# packages can't be restored (offline / locked-down network), it compiles the
# same test sources against the bundled MiniXunit shim and runs them instead.
# Usage: ./run-tests.sh [--offline]
set -euo pipefail
cd "$(dirname "$0")"

if [[ "${1:-}" != "--offline" ]] && dotnet restore tests/ReportGenerator.Tests >/dev/null 2>&1; then
  echo "==> xUnit via dotnet test"
  exec dotnet test tests/ReportGenerator.Tests --no-restore --nologo
fi

echo "==> NuGet unavailable or --offline: running the suite with the MiniXunit shim"
# The library and host have no package dependencies, so point restore at an empty local feed.
feed="$(mktemp -d)"
trap 'rm -rf "$feed"' EXIT
dotnet build tests/OfflineTestHost --nologo -v quiet -p:RestoreSources="$feed"
dotnet tests/OfflineTestHost/bin/Debug/net8.0/OfflineTestHost.dll
