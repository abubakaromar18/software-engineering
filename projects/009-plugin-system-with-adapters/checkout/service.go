// Package checkout is the application layer. It depends only on the
// payment.Processor port, never on a vendor package, so providers can be
// swapped or reordered purely through configuration.
package checkout

import (
	"context"
	"errors"
	"fmt"
	"io"
	"log/slog"

	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment"
)

// Order is what the shop wants paid.
type Order struct {
	ID     string // used as the idempotency key, so retries never double-charge
	Amount payment.Money
	Source string
}

// Attempt records one provider call, for observability and receipts.
type Attempt struct {
	Provider string
	Err      error
}

// Result is the outcome of Pay.
type Result struct {
	Receipt  payment.Receipt
	Attempts []Attempt
}

// ErrNoProviders is returned by New when the chain is empty.
var ErrNoProviders = errors.New("checkout: at least one payment provider is required")

// Service charges orders through an ordered chain of providers: the first is
// the primary, the rest are fallbacks used only when it is safe to do so.
type Service struct {
	chain []payment.Processor
	log   *slog.Logger
}

// New builds a Service. A nil logger discards logs.
func New(log *slog.Logger, chain ...payment.Processor) (*Service, error) {
	if len(chain) == 0 {
		return nil, ErrNoProviders
	}
	if log == nil {
		log = slog.New(slog.NewTextHandler(io.Discard, nil))
	}
	return &Service{chain: chain, log: log}, nil
}

// Pay charges the order. Failover rules:
//   - success or a decline/invalid/auth error stops immediately (another
//     provider would not change the answer, or it's a config bug to fix);
//   - a transient failure with a *known* outcome moves to the next provider;
//   - a transient failure with an *unknown* outcome stops, because the first
//     provider may still take the money.
func (s *Service) Pay(ctx context.Context, o Order) (Result, error) {
	req := payment.ChargeRequest{
		Amount:         o.Amount,
		Source:         o.Source,
		IdempotencyKey: "order-" + o.ID,
		Description:    "Order " + o.ID,
	}
	var (
		res     Result
		lastErr error
	)
	for _, p := range s.chain {
		receipt, err := p.Charge(ctx, req)
		res.Attempts = append(res.Attempts, Attempt{Provider: p.Name(), Err: err})
		if err == nil {
			s.log.Info("payment succeeded", "order", o.ID, "provider", p.Name(), "charge", receipt.ID)
			res.Receipt = receipt
			return res, nil
		}
		s.log.Warn("payment attempt failed", "order", o.ID, "provider", p.Name(), "err", err)
		lastErr = err
		if !payment.SafeToFailover(err) {
			break
		}
	}
	return res, fmt.Errorf("order %s: %w", o.ID, lastErr)
}
