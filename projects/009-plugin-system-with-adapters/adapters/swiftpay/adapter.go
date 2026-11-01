// Package swiftpay adapts the Swiftpay SDK to payment.Processor and registers
// itself as "swiftpay" when imported (blank-import to enable the plugin).
//
// Config keys:
//
//	api_key   required, e.g. "sp_test_123"
package swiftpay

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/registry"
	sdk "github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/vendors/swiftpay"
)

// Name is the registry key for this adapter.
const Name = "swiftpay"

func init() { registry.Register(Name, New) }

// Adapter wraps a Swiftpay client. It holds no business logic of its own:
// its only job is translating types, units and errors in both directions.
type Adapter struct {
	client *sdk.Client
}

// Compile-time proof that Adapter satisfies the port.
var _ payment.Processor = (*Adapter)(nil)

// New is the registry Factory.
func New(cfg registry.Config) (payment.Processor, error) {
	key, err := cfg.Require("api_key")
	if err != nil {
		return nil, err
	}
	client, err := sdk.NewClient(key)
	if err != nil {
		return nil, &payment.ProviderError{Provider: Name, Kind: payment.ErrAuth, Err: err}
	}
	return &Adapter{client: client}, nil
}

// Name implements payment.Processor.
func (a *Adapter) Name() string { return Name }

// Charge implements payment.Processor. Swiftpay already speaks minor units,
// so only the currency case and the error model need translating.
func (a *Adapter) Charge(ctx context.Context, req payment.ChargeRequest) (payment.Receipt, error) {
	if err := req.Validate(); err != nil {
		return payment.Receipt{}, err
	}
	// The SDK ignores context, so honour cancellation before the call.
	if err := ctx.Err(); err != nil {
		return payment.Receipt{}, fmt.Errorf("%s: %w", Name, err)
	}
	p, err := a.client.CreatePayment(sdk.PaymentParams{
		AmountCents:    req.Amount.Minor,
		Currency:       strings.ToLower(string(req.Amount.Currency)),
		Token:          req.Source,
		IdempotencyKey: req.IdempotencyKey,
		Memo:           req.Description,
	})
	if err != nil {
		return payment.Receipt{}, translate(err)
	}
	return payment.Receipt{
		ID:       p.ID,
		Provider: Name,
		Status:   payment.StatusSucceeded,
		Amount:   payment.Money{Minor: p.AmountCents, Currency: payment.Currency(strings.ToUpper(p.Currency))},
	}, nil
}

// Refund implements payment.Processor.
func (a *Adapter) Refund(ctx context.Context, req payment.RefundRequest) (payment.Receipt, error) {
	if err := req.Validate(); err != nil {
		return payment.Receipt{}, err
	}
	if err := ctx.Err(); err != nil {
		return payment.Receipt{}, fmt.Errorf("%s: %w", Name, err)
	}
	r, err := a.client.CreateRefund(req.ChargeID, req.Amount.Minor)
	if err != nil {
		return payment.Receipt{}, translate(err)
	}
	return payment.Receipt{ID: r.ID, Provider: Name, Status: payment.StatusRefunded, Amount: req.Amount}, nil
}

// translate maps Swiftpay's HTTP-status-based errors onto our error kinds.
func translate(err error) error {
	var apiErr *sdk.APIError
	if !errors.As(err, &apiErr) {
		return &payment.ProviderError{Provider: Name, Kind: payment.ErrUnavailable, Err: err}
	}
	var kind error
	switch s := apiErr.HTTPStatus; {
	case s == 401 || s == 403:
		kind = payment.ErrAuth
	case s == 402:
		kind = payment.ErrDeclined
	case s == 404:
		kind = payment.ErrNotFound
	case s == 429 || s >= 500:
		kind = payment.ErrUnavailable
	default:
		kind = payment.ErrInvalidRequest
	}
	return &payment.ProviderError{Provider: Name, Kind: kind, Code: apiErr.Code, Message: apiErr.Message, Err: err}
}
