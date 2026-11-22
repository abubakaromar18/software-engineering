package main

import (
	"bytes"
	"strings"
	"testing"
)

func runCLI(args ...string) (code int, stdout, stderr string) {
	var out, errb bytes.Buffer
	code = run(args, &out, &errb)
	return code, out.String(), errb.String()
}

func TestSimulatesBothPolicies(t *testing.T) {
	code, out, errOut := runCLI("-workload", "zipf", "-keys", "100", "-ops", "1000", "-capacity", "10")
	if code != 0 {
		t.Fatalf("exit %d, stderr: %s", code, errOut)
	}
	for _, want := range []string{"workload=zipf keys=100 ops=1000 capacity=10 seed=1", "LRU", "LFU", "hit-ratio"} {
		if !strings.Contains(out, want) {
			t.Errorf("output missing %q:\n%s", want, out)
		}
	}
}

func TestOutputIsReproducible(t *testing.T) {
	args := []string{"-workload", "shift", "-keys", "500", "-ops", "5000", "-capacity", "50", "-seed", "9"}
	_, a, _ := runCLI(args...)
	_, b, _ := runCLI(args...)
	if a != b {
		t.Fatalf("same flags, different output:\n%s\n---\n%s", a, b)
	}
}

func TestPolicyFilter(t *testing.T) {
	_, out, _ := runCLI("-policy", "LFU", "-ops", "100")
	if strings.Contains(out, "LRU") || !strings.Contains(out, "LFU") {
		t.Fatalf("-policy LFU should print only LFU:\n%s", out)
	}
}

func TestErrors(t *testing.T) {
	cases := []struct {
		name     string
		args     []string
		wantCode int
		wantErr  string
	}{
		{"unknown workload", []string{"-workload", "bogus"}, 1, `unknown workload "bogus"`},
		{"bad capacity", []string{"-capacity", "0"}, 1, "capacity must be at least 1"},
		{"bad policy", []string{"-policy", "fifo"}, 2, "-policy must be lru, lfu or all"},
		{"bad ops", []string{"-ops", "0"}, 2, "-ops must be positive"},
		{"stray args", []string{"extra"}, 2, "unexpected arguments"},
		{"bad flag", []string{"-nope"}, 2, "flag provided but not defined"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			code, _, errOut := runCLI(tc.args...)
			if code != tc.wantCode || !strings.Contains(errOut, tc.wantErr) {
				t.Fatalf("exit %d stderr %q; want exit %d containing %q", code, errOut, tc.wantCode, tc.wantErr)
			}
		})
	}
}

func TestHelpExitsZero(t *testing.T) {
	if code, _, errOut := runCLI("-h"); code != 0 || !strings.Contains(errOut, "-workload") {
		t.Fatalf("exit %d, usage: %s", code, errOut)
	}
}
