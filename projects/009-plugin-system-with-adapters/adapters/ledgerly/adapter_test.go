package ledgerly_test

import (
	"context"
	"errors"
	"testing"

	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/adapters/ledgerly"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment/paymenttest"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/registry"
)

func newAdapter(t *testing.T, secret string) payment.Processor {
	t.Helper()
	p, err := ledgerly.New(registry.Config{"merchant_id": "M1", "secret": secret})
	if err != nil {
		t.Fatal(err)
	}
	return p
}

func TestConformance(t *testing.T) {
	paymenttest.RunConformance(t, paymenttest.Harness{
		New:               func(t *testing.T) payment.Processor { return newAdapter(t, "s3cret") },
		ApprovedSource:    "card_ok",
		DeclinedSource:    "card_insufficient",
		UnavailableSource: "card_offline",
	})
}

func TestResultCodeMapping(t *testing.T) {
	ctx := context.Background()
	cases := []struct {
		source string
		want   error
		code   string
	}{
		{"card_insufficient", payment.ErrDeclined, "51"},
		{"card_stolen", payment.ErrDeclined, "05"},
		{"card_offline", payment.ErrUnavailable, "91"},
		{"card_network", payment.ErrUnavailable, ""}, // transport failure, no code
	}
	for _, tc := range cases {
		t.Run(tc.source, func(t *testing.T) {
			_, err := newAdapter(t, "s").Charge(ctx, payment.ChargeRequest{
				Amount: payment.Money{Minor: 100, Currency: "USD"}, Source: tc.source, IdempotencyKey: "k",
			})
			var pe *payment.ProviderError
			if !errors.Is(err, tc.want) || !errors.As(err, &pe) || pe.Code != tc.code {
				t.Fatalf("want %v code %q, got %v", tc.want, tc.code, err)
			}
		})
	}
}

func TestSecurityViolationMapsToAuth(t *testing.T) {
	_, err := newAdapter(t, "revoked").Charge(context.Background(), payment.ChargeRequest{
		Amount: payment.Money{Minor: 100, Currency: "USD"}, Source: "card_ok", IdempotencyKey: "k",
	})
	if !errors.Is(err, payment.ErrAuth) {
		t.Fatalf("want ErrAuth, got %v", err)
	}
}

func TestAmountsAreSentAsDecimalsPerCurrency(t *testing.T) {
	// JPY has no minor unit and KWD has three; refunding the exact charged
	// amount only succeeds if both legs used the same decimal rendering.
	ctx := context.Background()
	for _, m := range []payment.Money{{Minor: 500, Currency: "JPY"}, {Minor: 1250, Currency: "KWD"}} {
		p := newAdapter(t, "s")
		c, err := p.Charge(ctx, payment.ChargeRequest{Amount: m, Source: "card_ok", IdempotencyKey: string(m.Currency)})
		if err != nil {
			t.Fatal(err)
		}
		if _, err := p.Refund(ctx, payment.RefundRequest{ChargeID: c.ID, Amount: m}); err != nil {
			t.Fatalf("%v refund: %v", m, err)
		}
	}
}

func TestFailedChargeIsNotCachedForIdempotency(t *testing.T) {
	ctx := context.Background()
	p := newAdapter(t, "s")
	req := payment.ChargeRequest{Amount: payment.Money{Minor: 100, Currency: "USD"}, Source: "card_offline", IdempotencyKey: "retry-me"}
	if _, err := p.Charge(ctx, req); err == nil {
		t.Fatal("expected outage")
	}
	req.Source = "card_ok" // issuer is back; the same key may now succeed
	if _, err := p.Charge(ctx, req); err != nil {
		t.Fatalf("retry after failure should be allowed: %v", err)
	}
}

func TestFactoryRequiresCredentials(t *testing.T) {
	if _, err := ledgerly.New(registry.Config{"merchant_id": "M1"}); err == nil {
		t.Fatal("missing secret should fail")
	}
}
