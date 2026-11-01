package registry_test

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"sync"
	"testing"

	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/registry"
)

// stub is a minimal Processor used to exercise the registry in isolation.
type stub struct{ name string }

func (s stub) Name() string { return s.name }
func (s stub) Charge(context.Context, payment.ChargeRequest) (payment.Receipt, error) {
	return payment.Receipt{}, nil
}
func (s stub) Refund(context.Context, payment.RefundRequest) (payment.Receipt, error) {
	return payment.Receipt{}, nil
}

func factory(name string) registry.Factory {
	return func(registry.Config) (payment.Processor, error) { return stub{name}, nil }
}

func TestOpenIsCaseInsensitive(t *testing.T) {
	r := registry.New()
	if err := r.Register("Acme", factory("acme")); err != nil {
		t.Fatal(err)
	}
	p, err := r.Open("  ACME ", nil)
	if err != nil || p.Name() != "acme" {
		t.Fatalf("Open: %v %v", p, err)
	}
}

func TestDuplicateRegistrationIsRejected(t *testing.T) {
	r := registry.New()
	r.MustRegister("acme", factory("acme"))
	if err := r.Register("ACME", factory("other")); !errors.Is(err, registry.ErrDuplicateProvider) {
		t.Fatalf("want ErrDuplicateProvider, got %v", err)
	}
	defer func() {
		if recover() == nil {
			t.Fatal("MustRegister should panic on duplicates")
		}
	}()
	r.MustRegister("acme", factory("acme"))
}

func TestRegisterValidatesInput(t *testing.T) {
	r := registry.New()
	if err := r.Register(" ", factory("x")); err == nil {
		t.Error("empty name should fail")
	}
	if err := r.Register("x", nil); err == nil {
		t.Error("nil factory should fail")
	}
}

func TestUnknownProviderListsAlternatives(t *testing.T) {
	r := registry.New()
	r.MustRegister("beta", factory("beta"))
	r.MustRegister("alpha", factory("alpha"))
	_, err := r.Open("gamma", nil)
	if !errors.Is(err, registry.ErrUnknownProvider) || !strings.Contains(err.Error(), "alpha, beta") {
		t.Fatalf("got %v", err)
	}
}

func TestFactoryErrorIsWrapped(t *testing.T) {
	r := registry.New()
	boom := errors.New("boom")
	r.MustRegister("bad", func(registry.Config) (payment.Processor, error) { return nil, boom })
	if _, err := r.Open("bad", nil); !errors.Is(err, boom) {
		t.Fatalf("want wrapped boom, got %v", err)
	}
}

func TestConcurrentRegisterAndOpen(t *testing.T) {
	r := registry.New()
	var wg sync.WaitGroup
	for i := range 50 {
		wg.Add(2)
		name := fmt.Sprintf("p%d", i)
		go func() { defer wg.Done(); _ = r.Register(name, factory(name)) }()
		go func() { defer wg.Done(); _, _ = r.Open(name, nil); _ = r.Names() }()
	}
	wg.Wait()
	if got := len(r.Names()); got != 50 {
		t.Fatalf("want 50 providers, got %d", got)
	}
}

func TestConfigHelpers(t *testing.T) {
	c := registry.Config{"a": " x ", "blank": "  "}
	if v, err := c.Require("a"); err != nil || v != "x" {
		t.Fatalf("Require: %q %v", v, err)
	}
	if _, err := c.Require("blank"); err == nil {
		t.Fatal("blank value should count as missing")
	}
	if c.GetOr("missing", "d") != "d" || c.GetOr("a", "d") != "x" {
		t.Fatal("GetOr")
	}
}
