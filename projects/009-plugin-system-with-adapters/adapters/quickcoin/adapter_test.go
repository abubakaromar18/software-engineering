package quickcoin_test

import (
	"context"
	"errors"
	"testing"

	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/adapters/quickcoin"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment/paymenttest"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/registry"
)

func newAdapter(t *testing.T, extra registry.Config) payment.Processor {
	t.Helper()
	cfg := registry.Config{"api_token": "qc_test", "poll_interval": "1ms", "settle_timeout": "500ms", "polls_to_settle": "2"}
	for k, v := range extra {
		cfg[k] = v
	}
	p, err := quickcoin.New(cfg)
	if err != nil {
		t.Fatal(err)
	}
	return p
}

func TestConformance(t *testing.T) {
	paymenttest.RunConformance(t, paymenttest.Harness{
		New:               func(t *testing.T) payment.Processor { return newAdapter(t, nil) },
		ApprovedSource:    "wallet_alice",
		DeclinedSource:    "wallet_empty",
		UnavailableSource: "wallet_busy",
	})
}

func TestNeverSettlingInvoiceTimesOutWithUnknownOutcome(t *testing.T) {
	p := newAdapter(t, registry.Config{"settle_timeout": "20ms"})
	_, err := p.Charge(context.Background(), payment.ChargeRequest{
		Amount: payment.Money{Minor: 100, Currency: "USD"}, Source: "wallet_slow", IdempotencyKey: "k",
	})
	if !errors.Is(err, payment.ErrUnavailable) {
		t.Fatalf("want ErrUnavailable, got %v", err)
	}
	if !payment.Retryable(err) || payment.SafeToFailover(err) {
		t.Fatal("timeout after submit: retry same provider yes, fail over no")
	}
}

func TestUnsupportedCurrencyIsInvalid(t *testing.T) {
	_, err := newAdapter(t, nil).Charge(context.Background(), payment.ChargeRequest{
		Amount: payment.Money{Minor: 100, Currency: "JPY"}, Source: "wallet_alice", IdempotencyKey: "k",
	})
	if !errors.Is(err, payment.ErrInvalidRequest) {
		t.Fatalf("want ErrInvalidRequest, got %v", err)
	}
}

func TestPartialRefundIsUnsupported(t *testing.T) {
	ctx := context.Background()
	p := newAdapter(t, nil)
	c, err := p.Charge(ctx, payment.ChargeRequest{Amount: payment.Money{Minor: 1000, Currency: "EUR"}, Source: "wallet_alice", IdempotencyKey: "k"})
	if err != nil {
		t.Fatal(err)
	}
	_, err = p.Refund(ctx, payment.RefundRequest{ChargeID: c.ID, Amount: payment.Money{Minor: 400, Currency: "EUR"}})
	if !errors.Is(err, payment.ErrInvalidRequest) {
		t.Fatalf("want ErrInvalidRequest for partial reversal, got %v", err)
	}
}

func TestFactoryValidatesDurations(t *testing.T) {
	for _, cfg := range []registry.Config{
		{"api_token": "t", "poll_interval": "soon"},
		{"api_token": "t", "settle_timeout": "-1s"},
		{"api_token": "t", "polls_to_settle": "many"},
		{},
	} {
		if _, err := quickcoin.New(cfg); err == nil {
			t.Errorf("config %v should be rejected", cfg)
		}
	}
}
