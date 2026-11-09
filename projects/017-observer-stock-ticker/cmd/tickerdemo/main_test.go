package main

import (
	"bytes"
	"context"
	"strings"
	"testing"
	"time"
)

func TestRunReportsEveryObserver(t *testing.T) {
	var out bytes.Buffer
	cfg := config{duration: 100 * time.Millisecond, interval: time.Millisecond, slow: 5 * time.Millisecond, seed: 3}
	if err := run(context.Background(), cfg, &out); err != nil {
		t.Fatal(err)
	}
	for _, want := range []string{"ACME", "GLOBO", "INITECH", "board", "drop-oldest", "alert", "block", "slow-audit", "drop-newest", "alerts:"} {
		if !strings.Contains(out.String(), want) {
			t.Errorf("output missing %q:\n%s", want, out.String())
		}
	}
}

func TestRunRejectsInvalidInterval(t *testing.T) {
	var out bytes.Buffer
	if err := run(context.Background(), config{duration: time.Millisecond}, &out); err == nil {
		t.Fatal("expected an error for a zero interval")
	}
}
