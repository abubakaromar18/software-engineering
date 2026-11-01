package payment

import (
	"errors"
	"fmt"
)

// Sentinel error kinds. Callers branch on these with errors.Is and never need
// to know which vendor produced the failure or what its raw code was.
var (
	// ErrDeclined means the payment was refused (insufficient funds, fraud...).
	// Retrying with the same instrument will not help.
	ErrDeclined = errors.New("payment declined")
	// ErrInvalidRequest means the request itself was malformed or unsupported.
	ErrInvalidRequest = errors.New("invalid payment request")
	// ErrUnavailable means the provider could not be reached or timed out.
	// The request may be retried, possibly on a different provider.
	ErrUnavailable = errors.New("payment provider unavailable")
	// ErrAuth means the provider rejected our credentials (a configuration bug).
	ErrAuth = errors.New("payment provider authentication failed")
	// ErrNotFound means a referenced charge does not exist at the provider.
	ErrNotFound = errors.New("payment not found")
)

// ProviderError carries the normalised Kind plus the vendor's raw details so
// nothing useful is lost in translation (handy for logs and support tickets).
type ProviderError struct {
	Provider string // registry name of the adapter, e.g. "swiftpay"
	Kind     error  // one of the sentinel errors above
	Code     string // vendor's own error code, verbatim
	Message  string // vendor's human-readable message
	Err      error  // underlying cause, if any
	// OutcomeUnknown is set when the provider may still complete the
	// operation (e.g. a timeout after submission). Retrying on the *same*
	// provider with the same idempotency key is safe; switching providers
	// risks charging the customer twice.
	OutcomeUnknown bool
}

func (e *ProviderError) Error() string {
	msg := fmt.Sprintf("%s: %v", e.Provider, e.Kind)
	if e.Code != "" {
		msg += fmt.Sprintf(" (code %s)", e.Code)
	}
	if e.Message != "" {
		msg += ": " + e.Message
	}
	return msg
}

// Unwrap exposes both the normalised kind and the underlying cause, so
// errors.Is(err, payment.ErrDeclined) and errors.As(err, &vendorErr) both work.
func (e *ProviderError) Unwrap() []error {
	if e.Err == nil {
		return []error{e.Kind}
	}
	return []error{e.Kind, e.Err}
}

// Retryable reports whether retrying on the same provider (with the same
// idempotency key) may succeed.
func Retryable(err error) bool { return errors.Is(err, ErrUnavailable) }

// SafeToFailover reports whether the request may be sent to a *different*
// provider: the failure must be transient and known not to have taken money.
func SafeToFailover(err error) bool {
	if !Retryable(err) {
		return false
	}
	var pe *ProviderError
	if errors.As(err, &pe) && pe.OutcomeUnknown {
		return false
	}
	return true
}
