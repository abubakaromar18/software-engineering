#!/usr/bin/env bash
# Compiles and runs the test suite without Maven, using the JUnit 5 console launcher.
# Useful offline or where Maven Central is unreachable. Usage: ./run-tests.sh [junit-jar-dir]
set -euo pipefail
cd "$(dirname "$0")"
JARS="${1:-/usr/share/java}"
OUT="target/manual"
rm -rf "$OUT" && mkdir -p "$OUT/main" "$OUT/test"
CP="$JARS/junit-jupiter-api.jar:$JARS/junit-jupiter-params.jar:$JARS/apiguardian-api.jar:$JARS/opentest4j.jar:$JARS/junit-platform-commons.jar"
javac -Xlint:all -Werror --release 21 -d "$OUT/main" $(find src/main -name '*.java')
javac -Xlint:all -Werror --release 21 -cp "$OUT/main:$CP" -d "$OUT/test" $(find src/test -name '*.java')
java -jar "$JARS/junit-platform-console-standalone.jar" execute \
  -cp "$OUT/main:$OUT/test" --scan-classpath --details=summary --disable-banner
