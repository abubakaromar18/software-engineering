#!/usr/bin/env bash
# End-to-end checks of a real test binary's CLI: exit codes, selection,
# reporting and ordering. Usage: tests/selftest.sh path/to/sample_outcomes
set -u

BIN=${1:?usage: selftest.sh SAMPLE_BINARY}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
pass=0 fail=0

check() {   # check DESCRIPTION CONDITION...
    local desc=$1; shift
    if "$@"; then
        pass=$((pass + 1)); echo "  ok    $desc"
    else
        fail=$((fail + 1)); echo "  FAIL  $desc"
    fi
}

# run ARGS... -> sets $out and $code
run() { out=$("$BIN" --no-color "$@" 2>&1); code=$?; }
has() { grep -qF -- "$1" <<<"$out"; }
lacks() { ! has "$1"; }

echo "selftest: $BIN"

run --filter='math.addition_works,counter.*'
check "only passing tests selected -> exit 0" test "$code" -eq 0
check "summary counts two passes" has "[  PASSED  ] 2"

run --timeout=1 --junit="$TMP/report.xml"
check "full run exits 1" test "$code" -eq 1
check "assertion failure reported with location" has "sample_outcomes.c:"
check "both EXPECT failures shown" has '"&answer"'
check "crash contained and labelled" has "[  CRASHED ] platform.segfaults"
check "hang killed by timeout" has "[  TIMEOUT ] platform.hangs"
check "skip reason shown" has "not implemented yet"
check "failed list names every bad test" has "    platform.hangs (timed out)"
check "passing tests silent without -v" lacks "[       OK ]"

xml="$TMP/report.xml"
check "JUnit file written" test -s "$xml"
if command -v xmllint >/dev/null; then
    check "JUnit is well-formed XML" xmllint --noout "$xml"
fi
check "JUnit totals" grep -q 'tests="6" failures="1" errors="2" skipped="1"' "$xml"
check "JUnit escapes markup" grep -qF '&quot;&lt;answer&gt;&quot;' "$xml"
check "JUnit marks timeout as error" grep -q '<error type="timed out"' "$xml"

run --list --filter='-platform.*'
check "--list exits 0" test "$code" -eq 0
check "--list honours exclusions" test "$(wc -l <<<"$out")" -eq 4

run --filter='nothing.matches'
check "empty selection is a usage error" test "$code" -eq 2

run --bogus
check "unknown flag is a usage error" test "$code" -eq 2

run --timeout=1 --fail-fast --filter='platform.*'
check "--fail-fast stops after first failure" has "1 test ran"

run --filter='math.*' --seed=7 -v
first=$(grep -F '[ RUN      ]' <<<"$out")
run --filter='math.*' --seed=7 -v
second=$(grep -F '[ RUN      ]' <<<"$out")
check "same seed reproduces order" test "$first" = "$second"
check "seed is printed for reproduction" has "--seed=7"

run --no-fork --filter='math.*,counter.*' -v
check "--no-fork runs in-process" has "[       OK ] counter.starts_at_one"
check "--no-fork still reports failures" test "$code" -eq 1

echo "selftest: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
