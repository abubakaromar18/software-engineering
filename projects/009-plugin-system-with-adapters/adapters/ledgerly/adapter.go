// Package ledgerly adapts the Ledgerly gateway to payment.Processor and
// registers itself as "ledgerly" when imported.
//
// Config keys:
//
//	merchant_id   required
//	secret        required
package ledgerly

import (
	"context"
	"errors"
	"fmt"
	"sync"

	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/registry"
	sdk "github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/vendors/ledgerly"
)

// Name is the registry key for this adapter.
const Name = "ledgerly"

func init() { registry.Register(Name, New) }

// resultKinds maps ISO-8583 style result codes onto our error kinds. Codes
// not listed here are treated as declines: failing closed is the safe
// default for an unrecognised answer from a card network.
var resultKinds = map[string]error{
	sdk.DoNotHonour:        payment.ErrDeclined,
	sdk.InsufficientFunds:  payment.ErrDeclined,
	sdk.InvalidCard:        payment.ErrInvalidRequest,
	sdk.FormatError:        payment.ErrInvalidRequest,
	sdk.ExceedsOriginalAmt: payment.ErrInvalidRequest,
	sdk.UnableToLocate:     payment.ErrNotFound,
	sdk.SecurityViolation:  payment.ErrAuth,
	sdk.IssuerUnavailable:  payment.ErrUnavailable,
}

// Adapter wraps a Ledgerly gateway session.
//
// Ledgerly has no idempotency support, so the adapter supplies it with an
// in-process cache keyed by IdempotencyKey. Concurrent calls with the same
// key wait for the first one instead of charging twice.
type Adapter struct {
	gw *sdk.Gateway

	mu       sync.Mutex
	inflight map[string]*idemEntry
}

type idemEntry struct {
	done    chan struct{}
	receipt payment.Receipt
	err     error
}

var _ payment.Processor = (*Adapter)(nil)

// New is the registry Factory.
func New(cfg registry.Config) (payment.Processor, error) {
	merchant, err := cfg.Require("merchant_id")
	if err != nil {
		return nil, err
	}
	secret, err := cfg.Require("secret")
	if err != nil {
		return nil, err
	}
	return &Adapter{gw: sdk.Connect(merchant, secret), inflight: map[string]*idemEntry{}}, nil
}

// Name implements payment.Processor.
func (a *Adapter) Name() string { return Name }

// Charge implements payment.Processor.
func (a *Adapter) Charge(ctx context.Context, req payment.ChargeRequest) (payment.Receipt, error) {
	if err := req.Validate(); err != nil {
		return payment.Receipt{}, err
	}

	a.mu.Lock()
	if e, ok := a.inflight[req.IdempotencyKey]; ok {
		a.mu.Unlock()
		select {
		case <-e.done:
			return e.receipt, e.err
		case <-ctx.Done():
			return payment.Receipt{}, fmt.Errorf("%s: %w", Name, ctx.Err())
		}
	}
	e := &idemEntry{done: make(chan struct{})}
	a.inflight[req.IdempotencyKey] = e
	a.mu.Unlock()

	e.receipt, e.err = a.charge(ctx, req)
	if e.err != nil {
		// Only successes are remembered; a failed attempt may be retried.
		a.mu.Lock()
		delete(a.inflight, req.IdempotencyKey)
		a.mu.Unlock()
	}
	close(e.done)
	return e.receipt, e.err
}

func (a *Adapter) charge(ctx context.Context, req payment.ChargeRequest) (payment.Receipt, error) {
	resp, err := a.gw.Transact(ctx, sdk.TxnRequest{
		Type:         sdk.Sale,
		Amount:       req.Amount.Decimal(),
		CurrencyCode: string(req.Amount.Currency),
		CardRef:      req.Source,
		MerchantRef:  req.IdempotencyKey,
	})
	if err := check(resp, err); err != nil {
		return payment.Receipt{}, err
	}
	return payment.Receipt{ID: resp.TxnID, Provider: Name, Status: payment.StatusSucceeded, Amount: req.Amount}, nil
}

// Refund implements payment.Processor.
func (a *Adapter) Refund(ctx context.Context, req payment.RefundRequest) (payment.Receipt, error) {
	if err := req.Validate(); err != nil {
		return payment.Receipt{}, err
	}
	resp, err := a.gw.Transact(ctx, sdk.TxnRequest{
		Type:          sdk.Refund,
		Amount:        req.Amount.Decimal(),
		CurrencyCode:  string(req.Amount.Currency),
		OriginalTxnID: req.ChargeID,
	})
	if err := check(resp, err); err != nil {
		return payment.Receipt{}, err
	}
	return payment.Receipt{ID: resp.TxnID, Provider: Name, Status: payment.StatusRefunded, Amount: req.Amount}, nil
}

// check folds Ledgerly's two failure channels (Go error for transport,
// result code for business outcome) into one normalised error.
func check(resp sdk.TxnResponse, err error) error {
	if err != nil {
		if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
			return fmt.Errorf("%s: %w", Name, err)
		}
		return &payment.ProviderError{Provider: Name, Kind: payment.ErrUnavailable, Err: err}
	}
	if resp.ResultCode == sdk.Approved {
		return nil
	}
	kind, ok := resultKinds[resp.ResultCode]
	if !ok {
		kind = payment.ErrDeclined
	}
	return &payment.ProviderError{Provider: Name, Kind: kind, Code: resp.ResultCode, Message: resp.ResultText}
}
