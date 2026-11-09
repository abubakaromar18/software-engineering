// Command tickerdemo runs a simulated feed against three observers with
// different overflow policies, then reports how each one fared.
package main

import (
	"context"
	"flag"
	"fmt"
	"io"
	"os"
	"os/signal"
	"strings"
	"sync"
	"text/tabwriter"
	"time"

	"github.com/abubakaromar18/software-engineering/projects/017-observer-stock-ticker/feed"
	"github.com/abubakaromar18/software-engineering/projects/017-observer-stock-ticker/observer"
	"github.com/abubakaromar18/software-engineering/projects/017-observer-stock-ticker/ticker"
)

// alertMargin places the demo alert just above ACME's open so it tends to fire.
const alertMargin ticker.Cents = 25

// maxAlertsShown limits the report to the most recent alerts.
const maxAlertsShown = 3

type config struct {
	duration time.Duration
	interval time.Duration
	slow     time.Duration
	seed     uint64
}

var instruments = []feed.Instrument{{Symbol: "ACME", Open: 18_705}, {Symbol: "GLOBO", Open: 4_210}, {Symbol: "INITECH", Open: 9_933}}

func main() {
	var cfg config
	flag.DurationVar(&cfg.duration, "duration", 2*time.Second, "how long to run")
	flag.DurationVar(&cfg.interval, "interval", 5*time.Millisecond, "time between rounds of quotes")
	flag.DurationVar(&cfg.slow, "slow", 40*time.Millisecond, "time the slow observer spends per quote")
	flag.Uint64Var(&cfg.seed, "seed", 1, "random seed for the simulated feed")
	flag.Parse()

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()
	if err := run(ctx, cfg, os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "tickerdemo:", err)
		os.Exit(1)
	}
}

// consumer pairs an observer with the subscription settings that suit it.
type consumer struct {
	name     string
	opts     ticker.Options
	observer ticker.Observer
	sub      *ticker.Subscription
}

func run(ctx context.Context, cfg config, w io.Writer) error {
	f, err := feed.New(feed.Config{Instruments: instruments, Seed: cfg.seed, Interval: cfg.interval, MaxStepBps: 25})
	if err != nil {
		return err
	}

	board := observer.NewBoard()
	var alertsMu sync.Mutex
	var alerts []string
	alert := observer.NewCrossing("ACME", instruments[0].Open+alertMargin, func(q ticker.Quote, rising bool) {
		direction := "fell below"
		if rising {
			direction = "rose to"
		}
		alertsMu.Lock()
		defer alertsMu.Unlock()
		alerts = append(alerts, fmt.Sprintf("ACME %s %s (seq %d)", direction, q.Price, q.Seq))
	})
	audit := ticker.ObserverFunc(func(ticker.Quote) { time.Sleep(cfg.slow) })

	consumers := []*consumer{
		// The queue is shared across symbols, so it must fit a whole round: with
		// a smaller buffer, one symbol's quote evicts another's and the board
		// can miss a symbol entirely.
		{name: "board", opts: ticker.Options{Buffer: len(instruments), Policy: ticker.DropOldest}, observer: board},
		{name: "alert", opts: ticker.Options{Buffer: 64, Policy: ticker.Block, Symbols: []string{"ACME"}}, observer: alert},
		{name: "slow-audit", opts: ticker.Options{Buffer: 8, Policy: ticker.DropNewest}, observer: audit},
	}

	hub := ticker.NewHub()
	defer hub.Close()
	var wg sync.WaitGroup
	for _, c := range consumers {
		if c.sub, err = hub.Subscribe(c.opts); err != nil {
			return err
		}
		wg.Add(1)
		go func(c *consumer) {
			defer wg.Done()
			c.sub.Notify(c.observer)
		}(c)
	}

	runCtx, cancel := context.WithTimeout(ctx, cfg.duration)
	defer cancel()
	if err := f.Run(runCtx, hub); err != nil {
		return err
	}
	hub.Close()
	wg.Wait()

	report(w, consumers, board.Snapshot(), alerts)
	return nil
}

func report(w io.Writer, consumers []*consumer, quotes []ticker.Quote, alerts []string) {
	tw := tabwriter.NewWriter(w, 0, 0, 2, ' ', 0)
	fmt.Fprintln(tw, "SYMBOL\tLAST")
	for _, q := range quotes {
		fmt.Fprintf(tw, "%s\t%s\n", q.Symbol, q.Price)
	}
	fmt.Fprintln(tw, "\t")
	fmt.Fprintln(tw, "OBSERVER\tPOLICY\tBUFFER\tDELIVERED\tDROPPED")
	for _, c := range consumers {
		s := c.sub.Stats()
		fmt.Fprintf(tw, "%s\t%s\t%d\t%d\t%d\n", c.name, c.opts.Policy, c.opts.Buffer, s.Delivered, s.Dropped)
	}
	tw.Flush()
	fmt.Fprintf(w, "\nalerts: %d\n", len(alerts))
	if n := len(alerts); n > 0 {
		fmt.Fprintln(w, "  "+strings.Join(alerts[max(0, n-maxAlertsShown):], "\n  "))
	}
}
