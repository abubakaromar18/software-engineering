// Package ticker is an in-process publish/subscribe hub for stock quotes.
//
// Each subscriber gets its own bounded queue and its own delivery goroutine,
// so what happens when a consumer falls behind is an explicit, per-subscriber
// decision (see OverflowPolicy) rather than an accident of channel sizing.
package ticker

import (
	"fmt"
	"time"
)

// Cents is a price in integer cents. Integers keep equality and threshold
// comparisons exact, which float64 prices would not.
type Cents int64

// String formats the price as dollars, for example "187.05".
func (c Cents) String() string {
	sign := ""
	if c < 0 {
		sign = "-"
		c = -c
	}
	return fmt.Sprintf("%s%d.%02d", sign, int64(c)/100, int64(c)%100)
}

// Quote is one immutable price update. It is passed by value, so subscribers
// can never observe each other's modifications.
type Quote struct {
	Symbol string
	Price  Cents
	Seq    uint64 // assigned by the publisher; increases over time
	At     time.Time
}
