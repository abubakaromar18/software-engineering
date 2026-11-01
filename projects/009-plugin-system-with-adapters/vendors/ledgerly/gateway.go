// Package ledgerly simulates a fictional ISO-8583-flavoured card gateway.
//
// Ledgerly's quirks: one Transact call for every operation, amounts are
// decimal strings, business outcomes come back as two-character result codes
// in a successful response (a Go error only ever means a transport failure),
// and there is no idempotency support at all.
//
// Magic card refs: "card_insufficient" (51), "card_stolen" (05),
// "card_offline" (91, issuer unavailable), "card_network" (transport error).
// The secret "revoked" yields result code 63 (security violation).
package ledgerly

import (
	"context"
	"errors"
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"sync"
)

// TxnType selects the operation.
type TxnType string

const (
	Sale   TxnType = "SALE"
	Refund TxnType = "REFUND"
)

// Result codes (a subset of the ISO-8583 response codes).
const (
	Approved           = "00"
	DoNotHonour        = "05"
	InvalidCard        = "14"
	UnableToLocate     = "25"
	FormatError        = "30"
	InsufficientFunds  = "51"
	SecurityViolation  = "63"
	IssuerUnavailable  = "91"
	ExceedsOriginalAmt = "N3"
)

// ErrConnection is returned when the gateway cannot be reached.
var ErrConnection = errors.New("ledgerly: connection reset by peer")

// TxnRequest is a single gateway request.
type TxnRequest struct {
	Type          TxnType
	Amount        string // decimal, e.g. "12.34"
	CurrencyCode  string // upper case ISO code
	CardRef       string // SALE only
	OriginalTxnID string // REFUND only
	MerchantRef   string // free text, echoed back, NOT de-duplicated
}

// TxnResponse is the gateway's reply.
type TxnResponse struct {
	TxnID      string
	ResultCode string
	ResultText string
}

type sale struct {
	amount, refunded int64 // in "decimal digits with the point removed"
	currency         string
}

// Gateway is an in-memory stand-in for the Ledgerly gateway.
type Gateway struct {
	merchantID, secret string

	mu    sync.Mutex
	seq   int
	sales map[string]*sale
}

// Connect returns a gateway session for a merchant.
func Connect(merchantID, secret string) *Gateway {
	return &Gateway{merchantID: merchantID, secret: secret, sales: map[string]*sale{}}
}

var decimalRe = regexp.MustCompile(`^\d+(\.\d+)?$`)

// digits strips the decimal point; comparisons are only made between amounts
// of the same currency, which always share a format.
func digits(amount string) int64 {
	n, _ := strconv.ParseInt(strings.Replace(amount, ".", "", 1), 10, 64)
	return n
}

func reply(code, text string) TxnResponse { return TxnResponse{ResultCode: code, ResultText: text} }

// Transact performs one operation.
func (g *Gateway) Transact(ctx context.Context, req TxnRequest) (TxnResponse, error) {
	if err := ctx.Err(); err != nil {
		return TxnResponse{}, err
	}
	if req.CardRef == "card_network" {
		return TxnResponse{}, ErrConnection
	}
	if g.secret == "revoked" {
		return reply(SecurityViolation, "SECURITY VIOLATION"), nil
	}
	if !decimalRe.MatchString(req.Amount) || digits(req.Amount) == 0 || len(req.CurrencyCode) != 3 {
		return reply(FormatError, "FORMAT ERROR"), nil
	}

	g.mu.Lock()
	defer g.mu.Unlock()
	switch req.Type {
	case Sale:
		switch req.CardRef {
		case "":
			return reply(InvalidCard, "INVALID CARD"), nil
		case "card_insufficient":
			return reply(InsufficientFunds, "NOT SUFFICIENT FUNDS"), nil
		case "card_stolen":
			return reply(DoNotHonour, "DO NOT HONOUR"), nil
		case "card_offline":
			return reply(IssuerUnavailable, "ISSUER OR SWITCH INOPERATIVE"), nil
		}
		g.seq++
		id := fmt.Sprintf("LG%08d", g.seq)
		g.sales[id] = &sale{amount: digits(req.Amount), currency: req.CurrencyCode}
		return TxnResponse{TxnID: id, ResultCode: Approved, ResultText: "APPROVED"}, nil
	case Refund:
		s, ok := g.sales[req.OriginalTxnID]
		if !ok {
			return reply(UnableToLocate, "UNABLE TO LOCATE RECORD"), nil
		}
		amt := digits(req.Amount)
		if req.CurrencyCode != s.currency || s.refunded+amt > s.amount {
			return reply(ExceedsOriginalAmt, "EXCEEDS ORIGINAL AMOUNT"), nil
		}
		s.refunded += amt
		g.seq++
		return TxnResponse{TxnID: fmt.Sprintf("LG%08d", g.seq), ResultCode: Approved, ResultText: "APPROVED"}, nil
	default:
		return reply(FormatError, "UNKNOWN TXN TYPE"), nil
	}
}
