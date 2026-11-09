// Package feed generates a reproducible simulated market data stream, standing
// in for a real exchange connection.
package feed

import (
	"context"
	"errors"
	"math/rand/v2"
	"time"

	"github.com/abubakaromar18/software-engineering/projects/017-observer-stock-ticker/ticker"
)

// Publisher is the only thing a Feed needs from the outside world.
type Publisher interface {
	Publish(ctx context.Context, q ticker.Quote) error
}

// Instrument is a symbol and its opening price.
type Instrument struct {
	Symbol string
	Open   ticker.Cents
}

// Config configures a Feed.
type Config struct {
	Instruments []Instrument
	Seed        uint64
	Interval    time.Duration // time between rounds of quotes
	MaxStepBps  int           // largest move per tick, in basis points
}

// Feed moves each instrument by a bounded random walk. It is not safe for
// concurrent use; one goroutine owns it through Run.
type Feed struct {
	cfg    Config
	rng    *rand.Rand
	prices []ticker.Cents
	seq    uint64
	now    func() time.Time
}

// New validates cfg and returns a Feed positioned at the opening prices.
func New(cfg Config) (*Feed, error) {
	if len(cfg.Instruments) == 0 {
		return nil, errors.New("feed: at least one instrument is required")
	}
	if cfg.Interval <= 0 {
		return nil, errors.New("feed: interval must be positive")
	}
	if cfg.MaxStepBps <= 0 {
		return nil, errors.New("feed: max step must be positive")
	}
	prices := make([]ticker.Cents, len(cfg.Instruments))
	for i, in := range cfg.Instruments {
		if in.Open <= 0 {
			return nil, errors.New("feed: opening price must be positive for " + in.Symbol)
		}
		prices[i] = in.Open
	}
	return &Feed{
		cfg:    cfg,
		rng:    rand.New(rand.NewPCG(cfg.Seed, cfg.Seed)),
		prices: prices,
		now:    time.Now,
	}, nil
}

// Next advances every instrument once and returns the resulting quotes.
func (f *Feed) Next() []ticker.Quote {
	quotes := make([]ticker.Quote, len(f.prices))
	for i := range f.prices {
		bps := int64(f.rng.IntN(2*f.cfg.MaxStepBps+1) - f.cfg.MaxStepBps)
		next := f.prices[i] + ticker.Cents(int64(f.prices[i])*bps/10_000)
		if next < 1 {
			next = 1 // a price can approach zero but never reach it
		}
		f.prices[i] = next
		f.seq++
		quotes[i] = ticker.Quote{Symbol: f.cfg.Instruments[i].Symbol, Price: next, Seq: f.seq, At: f.now()}
	}
	return quotes
}

// Run publishes a round of quotes every interval until ctx ends, which is a
// normal shutdown and returns nil. Publisher failures are returned.
func (f *Feed) Run(ctx context.Context, p Publisher) error {
	tick := time.NewTicker(f.cfg.Interval)
	defer tick.Stop()
	for {
		select {
		case <-ctx.Done():
			return nil
		case <-tick.C:
			for _, q := range f.Next() {
				if err := p.Publish(ctx, q); err != nil {
					if ctx.Err() != nil {
						return nil
					}
					return err
				}
			}
		}
	}
}
