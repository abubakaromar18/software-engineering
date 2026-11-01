package payment

import (
	"context"
	"fmt"
	"strings"
)

// Processor is the one interface the application depends on. Every vendor
// integration is an Adapter that satisfies it. It is intentionally small:
// a narrow port is cheap to implement and easy to fake in tests.
type Processor interface {
	// Name returns the registry name of the provider, e.g. "swiftpay".
	Name() string
	// Charge captures funds. Requests with the same IdempotencyKey must not
	// be charged twice; the original Receipt is returned instead.
	Charge(ctx context.Context, req ChargeRequest) (Receipt, error)
	// Refund returns some or all of a previous charge.
	Refund(ctx context.Context, req RefundRequest) (Receipt, error)
}

// ChargeRequest is a provider-neutral request to take a payment.
type ChargeRequest struct {
	Amount         Money
	Source         string // tokenised payment instrument, e.g. "tok_visa"
	IdempotencyKey string // caller-chosen key that makes retries safe
	Description    string
}

// Validate checks invariants that hold for every provider.
func (r ChargeRequest) Validate() error {
	if _, err := r.Amount.Currency.Exponent(); err != nil {
		return err
	}
	if r.Amount.Minor <= 0 {
		return fmt.Errorf("%w: amount must be positive", ErrInvalidRequest)
	}
	if strings.TrimSpace(r.Source) == "" {
		return fmt.Errorf("%w: payment source is required", ErrInvalidRequest)
	}
	if strings.TrimSpace(r.IdempotencyKey) == "" {
		return fmt.Errorf("%w: idempotency key is required", ErrInvalidRequest)
	}
	return nil
}

// RefundRequest refunds part or all of an earlier charge.
type RefundRequest struct {
	ChargeID string // Receipt.ID of the original charge
	Amount   Money
}

// Validate checks invariants that hold for every provider.
func (r RefundRequest) Validate() error {
	if strings.TrimSpace(r.ChargeID) == "" {
		return fmt.Errorf("%w: charge id is required", ErrInvalidRequest)
	}
	if _, err := r.Amount.Currency.Exponent(); err != nil {
		return err
	}
	if r.Amount.Minor <= 0 {
		return fmt.Errorf("%w: refund amount must be positive", ErrInvalidRequest)
	}
	return nil
}

// Status is the normalised outcome of an operation.
type Status string

const (
	StatusSucceeded Status = "succeeded"
	StatusRefunded  Status = "refunded"
)

// Receipt is the provider-neutral result of a successful operation.
type Receipt struct {
	ID       string // provider's transaction id
	Provider string
	Status   Status
	Amount   Money
}
