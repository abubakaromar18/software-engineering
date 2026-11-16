#!/usr/bin/env bash
# Compiles and runs the test suite without Maven, using the JUnit 5 console launcher and
# locally installed jars (e.g. Debian/Ubuntu packages junit5, libmockito-java, libbyte-buddy-java,
# libobjenesis-java). Useful offline or where Maven Central is unreachable.
# Usage: ./run-tests.sh [jar-dir]
set -euo pipefail
cd "$(dirname "$0")"
JARS="${1:-/usr/share/java}"
OUT="target/manual"
rm -rf "$OUT" && mkdir -p "$OUT/main" "$OUT/test"
MOCKITO="$JARS/mockito-core.jar:$JARS/byte-buddy.jar:$JARS/byte-buddy-agent.jar:$JARS/objenesis.jar"
API="$JARS/junit-jupiter-api.jar:$JARS/junit-jupiter-params.jar:$JARS/apiguardian-api.jar:$JARS/opentest4j.jar:$JARS/junit-platform-commons.jar"
javac -Xlint:all -Werror --release 21 -d "$OUT/main" $(find src/main/java -name '*.java')
# -path: the distro mockito jar manifest lists optional jars that may not be installed
javac -Xlint:all,-path -Werror --release 21 -cp "$OUT/main:$API:$MOCKITO" -d "$OUT/test" $(find src/test/java -name '*.java')
java -jar "$JARS/junit-platform-console-standalone.jar" execute \
  -cp "$OUT/main:$OUT/test:$MOCKITO" --scan-classpath --details=tree --disable-banner
