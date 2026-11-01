package checkout_test

import (
	"context"
	"errors"
	"testing"

	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/checkout"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment"
)

// fake is a scripted Processor: it returns err if set, otherwise succeeds.
type fake struct {
	name  string
	err   error
	calls int
	keys  []string
}

func (f *fake) Name() string { return f.name }
func (f *fake) Charge(_ context.Context, r payment.ChargeRequest) (payment.Receipt, error) {
	f.calls++
	f.keys = append(f.keys, r.IdempotencyKey)
	if f.err != nil {
		return payment.Receipt{}, f.err
	}
	return payment.Receipt{ID: f.name + "-1", Provider: f.name, Status: payment.StatusSucceeded, Amount: r.Amount}, nil
}
func (f *fake) Refund(context.Context, payment.RefundRequest) (payment.Receipt, error) {
	return payment.Receipt{}, nil
}

func perr(kind error, unknown bool) error {
	return &payment.ProviderError{Provider: "x", Kind: kind, OutcomeUnknown: unknown}
}

var order = checkout.Order{ID: "42", Amount: payment.Money{Minor: 100, Currency: "USD"}, Source: "tok"}

func TestPrimarySuccessSkipsFallbacks(t *testing.T) {
	a, b := &fake{name: "a"}, &fake{name: "b"}
	svc, _ := checkout.New(nil, a, b)
	res, err := svc.Pay(context.Background(), order)
	if err != nil || res.Receipt.Provider != "a" || b.calls != 0 {
		t.Fatalf("res=%+v err=%v b.calls=%d", res, err, b.calls)
	}
	if a.keys[0] != "order-42" {
		t.Fatalf("idempotency key should derive from order id, got %q", a.keys[0])
	}
}

func TestFailoverRules(t *testing.T) {
	cases := []struct {
		name         string
		primaryErr   error
		wantFallback bool
		wantErr      error
	}{
		{"known outage fails over", perr(payment.ErrUnavailable, false), true, nil},
		{"unknown outcome stops", perr(payment.ErrUnavailable, true), false, payment.ErrUnavailable},
		{"decline stops", perr(payment.ErrDeclined, false), false, payment.ErrDeclined},
		{"auth error stops", perr(payment.ErrAuth, false), false, payment.ErrAuth},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			a, b := &fake{name: "a", err: tc.primaryErr}, &fake{name: "b"}
			svc, _ := checkout.New(nil, a, b)
			res, err := svc.Pay(context.Background(), order)
			if (b.calls == 1) != tc.wantFallback {
				t.Fatalf("fallback called %d times", b.calls)
			}
			if tc.wantErr == nil {
				if err != nil || res.Receipt.Provider != "b" || len(res.Attempts) != 2 {
					t.Fatalf("res=%+v err=%v", res, err)
				}
				if b.keys[0] != a.keys[0] {
					t.Fatal("fallback must reuse the same idempotency key")
				}
				return
			}
			if !errors.Is(err, tc.wantErr) || len(res.Attempts) != 1 {
				t.Fatalf("err=%v attempts=%d", err, len(res.Attempts))
			}
		})
	}
}

func TestAllProvidersDown(t *testing.T) {
	down := perr(payment.ErrUnavailable, false)
	svc, _ := checkout.New(nil, &fake{name: "a", err: down}, &fake{name: "b", err: down})
	res, err := svc.Pay(context.Background(), order)
	if !errors.Is(err, payment.ErrUnavailable) || len(res.Attempts) != 2 {
		t.Fatalf("err=%v attempts=%d", err, len(res.Attempts))
	}
}

func TestNewRequiresProviders(t *testing.T) {
	if _, err := checkout.New(nil); !errors.Is(err, checkout.ErrNoProviders) {
		t.Fatalf("got %v", err)
	}
}
