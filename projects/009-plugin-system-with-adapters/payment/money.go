// Package payment defines the provider-neutral domain model that every
// payment adapter must speak. Nothing in this package knows about any
// concrete vendor; vendors are adapted *to* these types, never the reverse.
package payment

import (
	"fmt"
	"strings"
)

// Currency is an ISO-4217 alphabetic code in upper case, e.g. "USD".
type Currency string

// exponents maps supported currencies to their number of minor-unit digits.
// Keeping this table small and explicit is deliberate: an unknown currency is
// rejected up front instead of being guessed at deep inside an adapter.
var exponents = map[Currency]int{
	"USD": 2,
	"EUR": 2,
	"GBP": 2,
	"JPY": 0,
	"KWD": 3,
}

// Exponent reports how many decimal places the currency uses.
func (c Currency) Exponent() (int, error) {
	exp, ok := exponents[c]
	if !ok {
		return 0, fmt.Errorf("%w: unsupported currency %q", ErrInvalidRequest, string(c))
	}
	return exp, nil
}

// Money is an amount in integer minor units (cents, pence, yen...).
// Integer minor units avoid floating-point rounding entirely.
type Money struct {
	Minor    int64
	Currency Currency
}

// NewMoney validates and constructs a Money value.
func NewMoney(minor int64, currency string) (Money, error) {
	c := Currency(strings.ToUpper(strings.TrimSpace(currency)))
	if _, err := c.Exponent(); err != nil {
		return Money{}, err
	}
	if minor <= 0 {
		return Money{}, fmt.Errorf("%w: amount must be positive, got %d", ErrInvalidRequest, minor)
	}
	return Money{Minor: minor, Currency: c}, nil
}

// Decimal renders the amount as a plain decimal string ("12.34", "500",
// "1.250") using the currency's exponent. Some vendors want this format.
func (m Money) Decimal() string {
	exp, err := m.Currency.Exponent()
	if err != nil || exp == 0 {
		return fmt.Sprintf("%d", m.Minor)
	}
	scale := int64(1)
	for i := 0; i < exp; i++ {
		scale *= 10
	}
	return fmt.Sprintf("%d.%0*d", m.Minor/scale, exp, m.Minor%scale)
}

// String implements fmt.Stringer, e.g. "12.34 USD".
func (m Money) String() string { return m.Decimal() + " " + string(m.Currency) }
