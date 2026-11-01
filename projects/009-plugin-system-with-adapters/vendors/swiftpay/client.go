// Package swiftpay simulates a fictional third-party payment SDK in memory.
//
// Treat everything under vendors/ as code we do not own and cannot change:
// its naming, units and error style deliberately differ from our domain
// model so the adapter has real translation work to do.
//
// Swiftpay's quirks: amounts are integer cents, currency codes must be lower
// case, errors are a typed *APIError carrying an HTTP status, idempotency is
// supported natively, and the client ignores context.Context entirely.
//
// Magic test tokens: "tok_decline" is declined, "tok_outage" simulates a 503.
// The API key "sp_test_revoked" is rejected with 401 on every call.
package swiftpay

import (
	"fmt"
	"strings"
	"sync"
)

// APIError is Swiftpay's error envelope.
type APIError struct {
	HTTPStatus int
	Type       string // "card_error", "invalid_request_error", "api_error", "authentication_error"
	Code       string // e.g. "card_declined", "resource_missing"
	Message    string
}

func (e *APIError) Error() string {
	return fmt.Sprintf("swiftpay %d %s/%s: %s", e.HTTPStatus, e.Type, e.Code, e.Message)
}

// PaymentParams describes a payment to create.
type PaymentParams struct {
	AmountCents    int64
	Currency       string // lower case, e.g. "usd"
	Token          string
	IdempotencyKey string
	Memo           string
}

// Payment is a Swiftpay payment object.
type Payment struct {
	ID            string
	AmountCents   int64
	Currency      string
	State         string // "paid", "partially_refunded", "refunded"
	RefundedCents int64
}

// Refund is a Swiftpay refund object.
type Refund struct {
	ID          string
	PaymentID   string
	AmountCents int64
}

// Client is an in-memory stand-in for the Swiftpay HTTP client.
type Client struct {
	apiKey string

	mu       sync.Mutex
	seq      int
	payments map[string]*Payment
	byIdem   map[string]string // idempotency key -> payment id
}

// NewClient validates the key format and returns a client.
func NewClient(apiKey string) (*Client, error) {
	if !strings.HasPrefix(apiKey, "sp_test_") {
		return nil, fmt.Errorf("swiftpay: api key must start with sp_test_ in sandbox mode")
	}
	return &Client{apiKey: apiKey, payments: map[string]*Payment{}, byIdem: map[string]string{}}, nil
}

func (c *Client) authorised() error {
	if c.apiKey == "sp_test_revoked" {
		return &APIError{401, "authentication_error", "invalid_api_key", "API key has been revoked"}
	}
	return nil
}

// CreatePayment charges a token.
func (c *Client) CreatePayment(p PaymentParams) (*Payment, error) {
	if err := c.authorised(); err != nil {
		return nil, err
	}
	if p.Currency != strings.ToLower(p.Currency) || len(p.Currency) != 3 {
		return nil, &APIError{400, "invalid_request_error", "invalid_currency", "currency must be a lower-case ISO code"}
	}
	if p.AmountCents <= 0 {
		return nil, &APIError{400, "invalid_request_error", "amount_too_small", "amount must be at least 1"}
	}
	switch p.Token {
	case "":
		return nil, &APIError{400, "invalid_request_error", "missing_token", "token is required"}
	case "tok_decline":
		return nil, &APIError{402, "card_error", "card_declined", "Your card was declined."}
	case "tok_outage":
		return nil, &APIError{503, "api_error", "service_unavailable", "Try again later."}
	}

	c.mu.Lock()
	defer c.mu.Unlock()
	if id, ok := c.byIdem[p.IdempotencyKey]; ok && p.IdempotencyKey != "" {
		cp := *c.payments[id]
		return &cp, nil
	}
	c.seq++
	pay := &Payment{ID: fmt.Sprintf("py_%06d", c.seq), AmountCents: p.AmountCents, Currency: p.Currency, State: "paid"}
	c.payments[pay.ID] = pay
	if p.IdempotencyKey != "" {
		c.byIdem[p.IdempotencyKey] = pay.ID
	}
	cp := *pay
	return &cp, nil
}

// CreateRefund refunds part or all of a payment.
func (c *Client) CreateRefund(paymentID string, amountCents int64) (*Refund, error) {
	if err := c.authorised(); err != nil {
		return nil, err
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	pay, ok := c.payments[paymentID]
	if !ok {
		return nil, &APIError{404, "invalid_request_error", "resource_missing", "No such payment: " + paymentID}
	}
	if amountCents <= 0 || pay.RefundedCents+amountCents > pay.AmountCents {
		return nil, &APIError{400, "invalid_request_error", "amount_too_large", "refund exceeds remaining amount"}
	}
	pay.RefundedCents += amountCents
	pay.State = "partially_refunded"
	if pay.RefundedCents == pay.AmountCents {
		pay.State = "refunded"
	}
	c.seq++
	return &Refund{ID: fmt.Sprintf("re_%06d", c.seq), PaymentID: paymentID, AmountCents: amountCents}, nil
}
