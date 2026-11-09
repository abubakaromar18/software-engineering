// Package observer holds concrete quote observers. They depend only on the
// ticker.Quote type, so each can be tested with no hub or goroutines at all.
package observer

import (
	"sort"
	"sync"

	"github.com/abubakaromar18/software-engineering/projects/017-observer-stock-ticker/ticker"
)

// Board tracks the latest quote per symbol. It is safe to read while another
// goroutine feeds it.
type Board struct {
	mu     sync.RWMutex
	latest map[string]ticker.Quote
}

// NewBoard returns an empty Board.
func NewBoard() *Board { return &Board{latest: make(map[string]ticker.Quote)} }

// OnQuote records q unless a newer quote for the symbol is already held.
func (b *Board) OnQuote(q ticker.Quote) {
	b.mu.Lock()
	defer b.mu.Unlock()
	if cur, ok := b.latest[q.Symbol]; !ok || q.Seq > cur.Seq {
		b.latest[q.Symbol] = q
	}
}

// Snapshot returns the latest quotes sorted by symbol.
func (b *Board) Snapshot() []ticker.Quote {
	b.mu.RLock()
	defer b.mu.RUnlock()
	out := make([]ticker.Quote, 0, len(b.latest))
	for _, q := range b.latest {
		out = append(out, q)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Symbol < out[j].Symbol })
	return out
}

// Crossing fires when a symbol's price crosses a level. It is edge-triggered,
// so a price hovering above the level alerts once rather than on every tick.
// The first quote only establishes which side the price starts on.
//
// A Crossing is meant to be driven by one goroutine, as Subscription.Notify does.
type Crossing struct {
	symbol  string
	level   ticker.Cents
	fire    func(q ticker.Quote, rising bool)
	started bool
	above   bool
}

// NewCrossing returns an alert on symbol at level, calling fire on each cross.
func NewCrossing(symbol string, level ticker.Cents, fire func(q ticker.Quote, rising bool)) *Crossing {
	return &Crossing{symbol: symbol, level: level, fire: fire}
}

// OnQuote updates the alert with q, ignoring other symbols.
func (c *Crossing) OnQuote(q ticker.Quote) {
	if q.Symbol != c.symbol {
		return
	}
	above := q.Price >= c.level
	if c.started && above != c.above {
		c.fire(q, above)
	}
	c.started, c.above = true, above
}
