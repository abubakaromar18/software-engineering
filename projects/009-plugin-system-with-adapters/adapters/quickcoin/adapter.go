// Package quickcoin adapts Quickcoin's asynchronous submit-then-poll API to
// the synchronous payment.Processor port, and registers itself as
// "quickcoin" when imported.
//
// Config keys:
//
//	api_token        required
//	poll_interval    optional Go duration, default 100ms
//	settle_timeout   optional Go duration, default 5s
//	polls_to_settle  optional int, sandbox latency simulation, default 3
package quickcoin

import (
	"context"
	"errors"
	"fmt"
	"strconv"
	"time"

	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/registry"
	sdk "github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/vendors/quickcoin"
)

// Name is the registry key for this adapter.
const Name = "quickcoin"

func init() { registry.Register(Name, New) }

// Adapter turns an async API into a blocking call by polling.
type Adapter struct {
	client        *sdk.Client
	pollInterval  time.Duration
	settleTimeout time.Duration
}

var _ payment.Processor = (*Adapter)(nil)

// New is the registry Factory.
func New(cfg registry.Config) (payment.Processor, error) {
	token, err := cfg.Require("api_token")
	if err != nil {
		return nil, err
	}
	interval, err := time.ParseDuration(cfg.GetOr("poll_interval", "100ms"))
	if err != nil || interval <= 0 {
		return nil, fmt.Errorf("invalid poll_interval %q", cfg["poll_interval"])
	}
	timeout, err := time.ParseDuration(cfg.GetOr("settle_timeout", "5s"))
	if err != nil || timeout <= 0 {
		return nil, fmt.Errorf("invalid settle_timeout %q", cfg["settle_timeout"])
	}
	polls, err := strconv.Atoi(cfg.GetOr("polls_to_settle", "3"))
	if err != nil || polls < 0 {
		return nil, fmt.Errorf("invalid polls_to_settle %q", cfg["polls_to_settle"])
	}
	return &Adapter{
		client:        sdk.New(sdk.Options{APIToken: token, PollsToSettle: polls}),
		pollInterval:  interval,
		settleTimeout: timeout,
	}, nil
}

// Name implements payment.Processor.
func (a *Adapter) Name() string { return Name }

// Charge implements payment.Processor: submit, then poll until the invoice
// reaches a terminal state, the settle timeout passes, or ctx is cancelled.
func (a *Adapter) Charge(ctx context.Context, req payment.ChargeRequest) (payment.Receipt, error) {
	if err := req.Validate(); err != nil {
		return payment.Receipt{}, err
	}
	if err := ctx.Err(); err != nil {
		return payment.Receipt{}, fmt.Errorf("%s: %w", Name, err)
	}
	// The idempotency key doubles as Quickcoin's nonce, which it de-duplicates.
	ticket, err := a.client.SubmitInvoice(req.Amount.Minor, string(req.Amount.Currency), req.Source, req.IdempotencyKey)
	if err != nil {
		return payment.Receipt{}, translate(err)
	}

	ctx, cancel := context.WithTimeout(ctx, a.settleTimeout)
	defer cancel()
	ticker := time.NewTicker(a.pollInterval)
	defer ticker.Stop()
	for {
		inv, err := a.client.InvoiceStatus(ticket)
		if err != nil {
			return payment.Receipt{}, translate(err)
		}
		switch inv.State {
		case sdk.Settled:
			return payment.Receipt{ID: ticket, Provider: Name, Status: payment.StatusSucceeded, Amount: req.Amount}, nil
		case sdk.Rejected:
			return payment.Receipt{}, &payment.ProviderError{Provider: Name, Kind: payment.ErrDeclined, Code: inv.State, Message: inv.Reason}
		}
		select {
		case <-ticker.C:
		case <-ctx.Done():
			if errors.Is(ctx.Err(), context.DeadlineExceeded) {
				// Outcome is unknown: the invoice may still settle later. Callers
				// must reconcile by ticket rather than blindly charge elsewhere.
				return payment.Receipt{}, &payment.ProviderError{
					Provider: Name, Kind: payment.ErrUnavailable, Code: "settle_timeout",
					Message: "invoice " + ticket + " still pending", Err: ctx.Err(),
					OutcomeUnknown: true,
				}
			}
			return payment.Receipt{}, fmt.Errorf("%s: %w", Name, ctx.Err())
		}
	}
}

// Refund implements payment.Processor. Quickcoin only supports full
// reversals; a partial refund surfaces as ErrInvalidRequest.
func (a *Adapter) Refund(ctx context.Context, req payment.RefundRequest) (payment.Receipt, error) {
	if err := req.Validate(); err != nil {
		return payment.Receipt{}, err
	}
	if err := ctx.Err(); err != nil {
		return payment.Receipt{}, fmt.Errorf("%s: %w", Name, err)
	}
	id, err := a.client.Reverse(req.ChargeID, req.Amount.Minor)
	if err != nil {
		return payment.Receipt{}, translate(err)
	}
	return payment.Receipt{ID: id, Provider: Name, Status: payment.StatusRefunded, Amount: req.Amount}, nil
}

func translate(err error) error {
	var kind error
	switch {
	case errors.Is(err, sdk.ErrUnauthorized):
		kind = payment.ErrAuth
	case errors.Is(err, sdk.ErrBadInput):
		kind = payment.ErrInvalidRequest
	case errors.Is(err, sdk.ErrUnknownTicket):
		kind = payment.ErrNotFound
	default: // ErrBusy and anything unexpected
		kind = payment.ErrUnavailable
	}
	return &payment.ProviderError{Provider: Name, Kind: kind, Message: err.Error(), Err: err}
}
