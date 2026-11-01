// Package paymenttest is a reusable contract-test suite for payment.Processor.
// Every adapter runs the same suite, so "it implements the interface" means
// "it behaves like the interface", not merely "it compiles". A new adapter
// gets dozens of behavioural checks for the cost of one Harness.
package paymenttest

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"testing"

	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment"
)

// Harness tells the suite how to build a fresh adapter and which magic
// sources trigger each outcome in that vendor's sandbox.
type Harness struct {
	New               func(t *testing.T) payment.Processor
	ApprovedSource    string
	DeclinedSource    string
	UnavailableSource string
	Currency          payment.Currency // a currency the provider supports
}

func usd(h Harness, minor int64) payment.Money {
	c := h.Currency
	if c == "" {
		c = "USD"
	}
	return payment.Money{Minor: minor, Currency: c}
}

// RunConformance runs the full contract against the harness.
func RunConformance(t *testing.T, h Harness) {
	t.Helper()
	ctx := context.Background()
	key := func(t *testing.T) string { return "key-" + t.Name() }

	t.Run("charge succeeds with normalised receipt", func(t *testing.T) {
		p := h.New(t)
		r, err := p.Charge(ctx, payment.ChargeRequest{Amount: usd(h, 1250), Source: h.ApprovedSource, IdempotencyKey: key(t)})
		if err != nil {
			t.Fatalf("Charge: %v", err)
		}
		if r.ID == "" || r.Provider != p.Name() || r.Status != payment.StatusSucceeded || r.Amount != usd(h, 1250) {
			t.Fatalf("unexpected receipt %+v", r)
		}
	})

	t.Run("same idempotency key never charges twice", func(t *testing.T) {
		p := h.New(t)
		req := payment.ChargeRequest{Amount: usd(h, 500), Source: h.ApprovedSource, IdempotencyKey: key(t)}
		first, err := p.Charge(ctx, req)
		if err != nil {
			t.Fatal(err)
		}
		second, err := p.Charge(ctx, req)
		if err != nil {
			t.Fatal(err)
		}
		if first.ID != second.ID {
			t.Fatalf("idempotent retry produced a new charge: %s vs %s", first.ID, second.ID)
		}
	})

	t.Run("concurrent duplicate requests charge once", func(t *testing.T) {
		p := h.New(t)
		req := payment.ChargeRequest{Amount: usd(h, 700), Source: h.ApprovedSource, IdempotencyKey: key(t)}
		const n = 8
		ids := make([]string, n)
		var wg sync.WaitGroup
		for i := range n {
			wg.Add(1)
			go func() {
				defer wg.Done()
				r, err := p.Charge(ctx, req)
				if err != nil {
					t.Error(err)
				}
				ids[i] = r.ID
			}()
		}
		wg.Wait()
		for _, id := range ids[1:] {
			if id != ids[0] {
				t.Fatalf("got different charge ids %v", ids)
			}
		}
	})

	t.Run("distinct keys produce distinct charges", func(t *testing.T) {
		p := h.New(t)
		seen := map[string]bool{}
		for i := range 3 {
			r, err := p.Charge(ctx, payment.ChargeRequest{Amount: usd(h, 100), Source: h.ApprovedSource, IdempotencyKey: fmt.Sprint(key(t), i)})
			if err != nil {
				t.Fatal(err)
			}
			if seen[r.ID] {
				t.Fatalf("duplicate id %s", r.ID)
			}
			seen[r.ID] = true
		}
	})

	t.Run("decline maps to ErrDeclined", func(t *testing.T) {
		p := h.New(t)
		_, err := p.Charge(ctx, payment.ChargeRequest{Amount: usd(h, 100), Source: h.DeclinedSource, IdempotencyKey: key(t)})
		if !errors.Is(err, payment.ErrDeclined) {
			t.Fatalf("want ErrDeclined, got %v", err)
		}
		var pe *payment.ProviderError
		if !errors.As(err, &pe) || pe.Provider != p.Name() {
			t.Fatalf("want *ProviderError naming %q, got %#v", p.Name(), err)
		}
		if payment.Retryable(err) {
			t.Fatal("a decline must not be retryable")
		}
	})

	t.Run("outage maps to retryable ErrUnavailable", func(t *testing.T) {
		p := h.New(t)
		_, err := p.Charge(ctx, payment.ChargeRequest{Amount: usd(h, 100), Source: h.UnavailableSource, IdempotencyKey: key(t)})
		if !errors.Is(err, payment.ErrUnavailable) || !payment.Retryable(err) {
			t.Fatalf("want retryable ErrUnavailable, got %v", err)
		}
	})

	t.Run("invalid request rejected before reaching vendor", func(t *testing.T) {
		p := h.New(t)
		_, err := p.Charge(ctx, payment.ChargeRequest{Amount: usd(h, 100), Source: "", IdempotencyKey: key(t)})
		if !errors.Is(err, payment.ErrInvalidRequest) {
			t.Fatalf("want ErrInvalidRequest, got %v", err)
		}
	})

	t.Run("full refund succeeds", func(t *testing.T) {
		p := h.New(t)
		c, err := p.Charge(ctx, payment.ChargeRequest{Amount: usd(h, 900), Source: h.ApprovedSource, IdempotencyKey: key(t)})
		if err != nil {
			t.Fatal(err)
		}
		r, err := p.Refund(ctx, payment.RefundRequest{ChargeID: c.ID, Amount: c.Amount})
		if err != nil {
			t.Fatalf("Refund: %v", err)
		}
		if r.Status != payment.StatusRefunded || r.Amount != c.Amount || r.ID == "" || r.ID == c.ID {
			t.Fatalf("unexpected refund receipt %+v", r)
		}
	})

	t.Run("refund of unknown charge maps to ErrNotFound", func(t *testing.T) {
		p := h.New(t)
		_, err := p.Refund(ctx, payment.RefundRequest{ChargeID: "does-not-exist", Amount: usd(h, 100)})
		if !errors.Is(err, payment.ErrNotFound) {
			t.Fatalf("want ErrNotFound, got %v", err)
		}
	})

	t.Run("cancelled context is honoured", func(t *testing.T) {
		p := h.New(t)
		cctx, cancel := context.WithCancel(ctx)
		cancel()
		_, err := p.Charge(cctx, payment.ChargeRequest{Amount: usd(h, 100), Source: h.ApprovedSource, IdempotencyKey: key(t)})
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("want context.Canceled, got %v", err)
		}
	})
}
