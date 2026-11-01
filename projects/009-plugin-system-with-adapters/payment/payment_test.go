package payment_test

import (
	"errors"
	"fmt"
	"testing"

	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment"
)

func TestDecimalRespectsCurrencyExponent(t *testing.T) {
	cases := map[payment.Money]string{
		{Minor: 1999, Currency: "USD"}: "19.99",
		{Minor: 5, Currency: "EUR"}:    "0.05",
		{Minor: 500, Currency: "JPY"}:  "500",
		{Minor: 1250, Currency: "KWD"}: "1.250",
	}
	for m, want := range cases {
		if got := m.Decimal(); got != want {
			t.Errorf("%v: got %q want %q", m, got, want)
		}
	}
}

func TestNewMoneyValidates(t *testing.T) {
	if m, err := payment.NewMoney(100, " usd "); err != nil || m.Currency != "USD" {
		t.Fatalf("got %v %v", m, err)
	}
	for _, tc := range []struct {
		minor int64
		cur   string
	}{{0, "USD"}, {-5, "USD"}, {100, "XXX"}} {
		if _, err := payment.NewMoney(tc.minor, tc.cur); !errors.Is(err, payment.ErrInvalidRequest) {
			t.Errorf("%v: want ErrInvalidRequest, got %v", tc, err)
		}
	}
}

func TestChargeRequestValidate(t *testing.T) {
	ok := payment.ChargeRequest{Amount: payment.Money{Minor: 1, Currency: "USD"}, Source: "s", IdempotencyKey: "k"}
	if err := ok.Validate(); err != nil {
		t.Fatal(err)
	}
	noKey := ok
	noKey.IdempotencyKey = ""
	if !errors.Is(noKey.Validate(), payment.ErrInvalidRequest) {
		t.Fatal("missing idempotency key should be invalid")
	}
}

func TestProviderErrorUnwrapsToKindAndCause(t *testing.T) {
	cause := errors.New("vendor said no")
	err := fmt.Errorf("checkout: %w", &payment.ProviderError{Provider: "acme", Kind: payment.ErrDeclined, Code: "51", Err: cause})
	if !errors.Is(err, payment.ErrDeclined) || !errors.Is(err, cause) {
		t.Fatalf("unwrap chain broken: %v", err)
	}
	if got := err.Error(); got != "checkout: acme: payment declined (code 51)" {
		t.Fatalf("message: %q", got)
	}
}

func TestFailoverSafety(t *testing.T) {
	known := &payment.ProviderError{Provider: "a", Kind: payment.ErrUnavailable}
	unknown := &payment.ProviderError{Provider: "a", Kind: payment.ErrUnavailable, OutcomeUnknown: true}
	declined := &payment.ProviderError{Provider: "a", Kind: payment.ErrDeclined}
	if !payment.SafeToFailover(known) || payment.SafeToFailover(unknown) || payment.SafeToFailover(declined) {
		t.Fatal("SafeToFailover rules violated")
	}
	if !payment.Retryable(unknown) {
		t.Fatal("unknown outcome is still retryable on the same provider")
	}
}
