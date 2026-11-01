// Package quickcoin simulates a fictional asynchronous wallet-payment API.
//
// Quickcoin's quirks: payments are asynchronous (submit an invoice, then poll
// its status until it settles), only USD and EUR are accepted, only *full*
// reversals are supported, and errors are package-level sentinel values.
// Submitting the same nonce twice returns the original ticket.
//
// Magic wallets: "wallet_empty" is rejected, "wallet_slow" never settles.
package quickcoin

import (
	"errors"
	"fmt"
	"sync"
)

// Sentinel errors.
var (
	ErrUnauthorized  = errors.New("quickcoin: unauthorized")
	ErrBadInput      = errors.New("quickcoin: bad input")
	ErrUnknownTicket = errors.New("quickcoin: unknown ticket")
	ErrBusy          = errors.New("quickcoin: busy, retry later")
)

// Invoice states.
const (
	Pending  = "pending"
	Settled  = "settled"
	Rejected = "rejected"
	Reversed = "reversed"
)

// Invoice is the status of a submitted payment.
type Invoice struct {
	Ticket      string
	State       string
	Reason      string // set when Rejected
	AmountMinor int64
	Currency    string
}

// Options configures the client.
type Options struct {
	APIToken string
	// PollsToSettle is how many status polls an invoice stays pending for
	// before settling. Simulates network/ledger latency.
	PollsToSettle int
}

type invoice struct {
	Invoice
	polls int
}

// Client is an in-memory stand-in for the Quickcoin API.
type Client struct {
	opts Options

	mu       sync.Mutex
	seq      int
	invoices map[string]*invoice
	byNonce  map[string]string
}

// New creates a client.
func New(opts Options) *Client {
	return &Client{opts: opts, invoices: map[string]*invoice{}, byNonce: map[string]string{}}
}

// SubmitInvoice starts an asynchronous payment and returns its ticket.
func (c *Client) SubmitInvoice(amountMinor int64, currency, wallet, nonce string) (string, error) {
	if c.opts.APIToken == "" || c.opts.APIToken == "revoked" {
		return "", ErrUnauthorized
	}
	if currency != "USD" && currency != "EUR" {
		return "", fmt.Errorf("%w: currency %s not supported", ErrBadInput, currency)
	}
	if amountMinor <= 0 || wallet == "" || nonce == "" {
		return "", fmt.Errorf("%w: amount, wallet and nonce are required", ErrBadInput)
	}
	if wallet == "wallet_busy" {
		return "", ErrBusy
	}

	c.mu.Lock()
	defer c.mu.Unlock()
	if t, ok := c.byNonce[nonce]; ok {
		return t, nil
	}
	c.seq++
	inv := &invoice{Invoice: Invoice{Ticket: fmt.Sprintf("qc-%d", c.seq), State: Pending, AmountMinor: amountMinor, Currency: currency}}
	if wallet == "wallet_empty" {
		inv.State, inv.Reason = Rejected, "insufficient balance"
	}
	if wallet == "wallet_slow" {
		inv.polls = -1 << 30 // effectively never settles
	}
	c.invoices[inv.Ticket] = inv
	c.byNonce[nonce] = inv.Ticket
	return inv.Ticket, nil
}

// InvoiceStatus polls an invoice. Each poll advances simulated time.
func (c *Client) InvoiceStatus(ticket string) (Invoice, error) {
	if c.opts.APIToken == "revoked" {
		return Invoice{}, ErrUnauthorized
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	inv, ok := c.invoices[ticket]
	if !ok {
		return Invoice{}, ErrUnknownTicket
	}
	if inv.State == Pending {
		inv.polls++
		if inv.polls >= c.opts.PollsToSettle {
			inv.State = Settled
		}
	}
	return inv.Invoice, nil
}

// Reverse fully reverses a settled invoice and returns a reversal ticket.
func (c *Client) Reverse(ticket string, amountMinor int64) (string, error) {
	if c.opts.APIToken == "revoked" {
		return "", ErrUnauthorized
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	inv, ok := c.invoices[ticket]
	if !ok {
		return "", ErrUnknownTicket
	}
	if inv.State != Settled {
		return "", fmt.Errorf("%w: invoice is %s", ErrBadInput, inv.State)
	}
	if amountMinor != inv.AmountMinor {
		return "", fmt.Errorf("%w: only full reversals are supported", ErrBadInput)
	}
	inv.State = Reversed
	c.seq++
	return fmt.Sprintf("qc-rev-%d", c.seq), nil
}
