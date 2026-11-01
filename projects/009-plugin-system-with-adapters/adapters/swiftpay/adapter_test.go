package swiftpay_test

import (
	"context"
	"errors"
	"testing"

	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/adapters/swiftpay"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment/paymenttest"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/registry"
	sdk "github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/vendors/swiftpay"
)

func newAdapter(t *testing.T, key string) payment.Processor {
	t.Helper()
	p, err := swiftpay.New(registry.Config{"api_key": key})
	if err != nil {
		t.Fatal(err)
	}
	return p
}

func TestConformance(t *testing.T) {
	paymenttest.RunConformance(t, paymenttest.Harness{
		New:               func(t *testing.T) payment.Processor { return newAdapter(t, "sp_test_1") },
		ApprovedSource:    "tok_visa",
		DeclinedSource:    "tok_decline",
		UnavailableSource: "tok_outage",
	})
}

func TestSelfRegisters(t *testing.T) {
	p, err := registry.Open("swiftpay", registry.Config{"api_key": "sp_test_x"})
	if err != nil || p.Name() != "swiftpay" {
		t.Fatalf("Open: %v, %v", p, err)
	}
}

func TestFactoryRejectsBadConfig(t *testing.T) {
	if _, err := swiftpay.New(registry.Config{}); err == nil {
		t.Fatal("missing api_key should fail")
	}
	_, err := swiftpay.New(registry.Config{"api_key": "live_123"})
	if !errors.Is(err, payment.ErrAuth) {
		t.Fatalf("non-sandbox key: want ErrAuth, got %v", err)
	}
}

func TestRevokedKeyMapsToErrAuthAndKeepsVendorError(t *testing.T) {
	p := newAdapter(t, "sp_test_revoked")
	_, err := p.Charge(context.Background(), payment.ChargeRequest{
		Amount: payment.Money{Minor: 100, Currency: "USD"}, Source: "tok_visa", IdempotencyKey: "k",
	})
	if !errors.Is(err, payment.ErrAuth) {
		t.Fatalf("want ErrAuth, got %v", err)
	}
	var apiErr *sdk.APIError
	if !errors.As(err, &apiErr) || apiErr.HTTPStatus != 401 {
		t.Fatalf("vendor error should stay reachable via errors.As, got %v", err)
	}
}

func TestPartialRefundsThenOverRefundIsInvalid(t *testing.T) {
	ctx := context.Background()
	p := newAdapter(t, "sp_test_1")
	c, err := p.Charge(ctx, payment.ChargeRequest{Amount: payment.Money{Minor: 1000, Currency: "EUR"}, Source: "tok_visa", IdempotencyKey: "k"})
	if err != nil {
		t.Fatal(err)
	}
	if c.Amount.Currency != "EUR" {
		t.Fatalf("currency not normalised back to upper case: %v", c.Amount)
	}
	part := payment.Money{Minor: 600, Currency: "EUR"}
	if _, err := p.Refund(ctx, payment.RefundRequest{ChargeID: c.ID, Amount: part}); err != nil {
		t.Fatal(err)
	}
	_, err = p.Refund(ctx, payment.RefundRequest{ChargeID: c.ID, Amount: part})
	if !errors.Is(err, payment.ErrInvalidRequest) {
		t.Fatalf("over-refund: want ErrInvalidRequest, got %v", err)
	}
}
