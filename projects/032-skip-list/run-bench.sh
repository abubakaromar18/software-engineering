#!/usr/bin/env bash
# Compiles the main sources with plain javac and runs the SkipListMap-vs-TreeMap benchmark.
# Usage: ./run-bench.sh [size] [seed]
set -euo pipefail
cd "$(dirname "$0")"
OUT="target/manual/main"
mkdir -p "$OUT"
javac -Xlint:all -Werror --release 21 -d "$OUT" $(find src/main/java -name '*.java')
java -cp "$OUT" dev.omar.skiplist.bench.Benchmark "$@"
