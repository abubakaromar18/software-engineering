#!/usr/bin/env bash
# Compiles and runs the test suite without Gradle, using the Kotlin compiler and JUnit 4
# jars that ship inside a Gradle 8.x distribution. Useful offline or where Maven Central
# is unreachable. Usage: ./run-tests.sh [gradle-lib-dir]
set -euo pipefail
cd "$(dirname "$0")"
LIB="${1:-${GRADLE_HOME:-/opt/gradle}/lib}"
OUT="build/manual"
KOTLIN_VERSION="2.0.21"

STDLIB="$LIB/kotlin-stdlib-$KOTLIN_VERSION.jar"
COMPILER_CP=$(printf '%s:' \
  "$LIB/kotlin-compiler-embeddable-$KOTLIN_VERSION.jar" "$STDLIB" \
  "$LIB/kotlin-script-runtime-$KOTLIN_VERSION.jar" "$LIB/kotlin-reflect-$KOTLIN_VERSION.jar" \
  "$LIB/kotlin-daemon-embeddable-$KOTLIN_VERSION.jar" "$LIB"/trove4j-*.jar "$LIB"/annotations-*.jar \
  "$LIB"/kotlinx-coroutines-core-jvm-*.jar)
TEST_CP="$LIB/junit-4.13.2.jar:$LIB/hamcrest-core-1.3.jar"

kotlinc() {
  java -cp "$COMPILER_CP" org.jetbrains.kotlin.cli.jvm.K2JVMCompiler \
    -no-stdlib -no-reflect -jvm-target 21 -Werror "$@"
}

rm -rf "$OUT" && mkdir -p "$OUT/main" "$OUT/test"
echo "Compiling main sources..."
kotlinc -cp "$STDLIB" -d "$OUT/main" src/main/kotlin
echo "Compiling tests..."
# -Xfriend-paths lets tests see `internal` declarations, as Gradle does.
kotlinc -cp "$STDLIB:$OUT/main:$TEST_CP" -Xfriend-paths="$OUT/main" -d "$OUT/test" src/test/kotlin

classes=$(cd "$OUT/test" && find . -name '*Test.class' | sed 's|^\./||; s|\.class$||; s|/|.|g' | sort)
java -cp "$STDLIB:$OUT/main:$OUT/test:$TEST_CP" org.junit.runner.JUnitCore $classes
