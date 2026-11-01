package main

import (
	"bytes"
	"errors"
	"strings"
	"testing"

	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment"
)

func noEnv(string) string { return "" }

func TestListShowsAllBundledPlugins(t *testing.T) {
	var out bytes.Buffer
	if err := run([]string{"-list"}, &out, noEnv); err != nil {
		t.Fatal(err)
	}
	if got := out.String(); got != "ledgerly\nquickcoin\nswiftpay\n" {
		t.Fatalf("got %q", got)
	}
}

func TestFailoverAndRefundEndToEnd(t *testing.T) {
	var out bytes.Buffer
	err := run([]string{"-providers", "swiftpay,ledgerly", "-source", "tok_outage", "-order", "o1", "-refund"}, &out, noEnv)
	if err != nil {
		t.Fatal(err)
	}
	s := out.String()
	for _, want := range []string{"attempt 1  swiftpay", "attempt 2  ledgerly   ok", "charged    19.99 USD via ledgerly", "refunded   19.99 USD via ledgerly"} {
		if !strings.Contains(s, want) {
			t.Errorf("output missing %q:\n%s", want, s)
		}
	}
}

func TestDeclineExitCode(t *testing.T) {
	err := run([]string{"-source", "tok_decline"}, &bytes.Buffer{}, noEnv)
	if !errors.Is(err, payment.ErrDeclined) || exitCode(err) != 2 {
		t.Fatalf("err=%v code=%d", err, exitCode(err))
	}
}

func TestEnvOverridesSandboxDefaults(t *testing.T) {
	env := map[string]string{"SWIFTPAY_API_KEY": "sp_test_revoked"}
	err := run([]string{"-providers", "swiftpay"}, &bytes.Buffer{}, func(k string) string { return env[k] })
	if !errors.Is(err, payment.ErrAuth) || exitCode(err) != 1 {
		t.Fatalf("want ErrAuth from overridden key, got %v", err)
	}
}

func TestUnknownProvider(t *testing.T) {
	if err := run([]string{"-providers", "nope"}, &bytes.Buffer{}, noEnv); err == nil {
		t.Fatal("expected error")
	}
}
