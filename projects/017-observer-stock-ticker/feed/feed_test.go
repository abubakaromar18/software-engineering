package feed

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/abubakaromar18/software-engineering/projects/017-observer-stock-ticker/ticker"
)

func cfg(seed uint64) Config {
	return Config{
		Instruments: []Instrument{{"ACME", 10_000}, {"GLOBO", 2_500}},
		Seed:        seed, Interval: time.Millisecond, MaxStepBps: 50,
	}
}

func mustNew(t *testing.T, c Config) *Feed {
	t.Helper()
	f, err := New(c)
	if err != nil {
		t.Fatal(err)
	}
	return f
}

func TestSameSeedProducesSamePrices(t *testing.T) {
	a, b := mustNew(t, cfg(42)), mustNew(t, cfg(42))
	for i := 0; i < 100; i++ {
		qa, qb := a.Next(), b.Next()
		for j := range qa {
			if qa[j].Price != qb[j].Price || qa[j].Seq != qb[j].Seq {
				t.Fatalf("round %d diverged: %+v vs %+v", i, qa[j], qb[j])
			}
		}
	}
}

func TestStepsStayBoundedAndPositive(t *testing.T) {
	f := mustNew(t, cfg(7))
	prev := []ticker.Cents{10_000, 2_500}
	for i := 0; i < 5000; i++ {
		for j, q := range f.Next() {
			limit := int64(prev[j]) * 50 / 10_000
			if d := int64(q.Price - prev[j]); q.Price < 1 || d > limit || d < -limit {
				t.Fatalf("bad step %d -> %d", prev[j], q.Price)
			}
			prev[j] = q.Price
		}
	}
}

func TestNewRejectsBadConfig(t *testing.T) {
	bad := map[string]func(*Config){
		"no instruments": func(c *Config) { c.Instruments = nil },
		"zero interval":  func(c *Config) { c.Interval = 0 },
		"zero step":      func(c *Config) { c.MaxStepBps = 0 },
		"bad open":       func(c *Config) { c.Instruments = []Instrument{{"X", 0}} },
	}
	for name, mutate := range bad {
		c := cfg(1)
		mutate(&c)
		if _, err := New(c); err == nil {
			t.Errorf("%s: expected an error", name)
		}
	}
}

type publisherFunc func(context.Context, ticker.Quote) error

func (f publisherFunc) Publish(ctx context.Context, q ticker.Quote) error { return f(ctx, q) }

func TestRunStopsCleanlyWhenContextEnds(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	seen := 0
	err := mustNew(t, cfg(1)).Run(ctx, publisherFunc(func(context.Context, ticker.Quote) error {
		if seen++; seen == 10 {
			cancel()
		}
		return nil
	}))
	if err != nil || seen < 10 {
		t.Fatalf("err=%v seen=%d", err, seen)
	}
}

func TestRunReturnsPublisherError(t *testing.T) {
	boom := errors.New("boom")
	err := mustNew(t, cfg(1)).Run(context.Background(), publisherFunc(func(context.Context, ticker.Quote) error {
		return boom
	}))
	if !errors.Is(err, boom) {
		t.Fatalf("got %v", err)
	}
}
