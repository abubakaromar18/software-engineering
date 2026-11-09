package ticker

import (
	"context"
	"fmt"
	"sync"
	"sync/atomic"
)

// OverflowPolicy decides what Publish does when a subscriber's queue is full.
type OverflowPolicy int

const (
	// Block makes the publisher wait for room. Nothing is lost, but this
	// subscriber can stall the whole feed. It is the zero value because
	// silently losing data should be something a caller opts in to.
	Block OverflowPolicy = iota
	// DropOldest evicts the oldest queued quote. Best for "latest value
	// wins" consumers such as a price display.
	DropOldest
	// DropNewest discards the incoming quote. Best for consumers that care
	// about a contiguous prefix more than about freshness.
	DropNewest
)

// String returns the policy's name.
func (p OverflowPolicy) String() string {
	switch p {
	case Block:
		return "block"
	case DropOldest:
		return "drop-oldest"
	case DropNewest:
		return "drop-newest"
	default:
		return fmt.Sprintf("OverflowPolicy(%d)", int(p))
	}
}

// Stats is a point-in-time view of a subscription's counters.
type Stats struct {
	Delivered uint64 // quotes handed to the consumer
	Dropped   uint64 // quotes lost to the overflow policy
}

// Observer receives quotes. It is the classic Observer-pattern callback,
// layered on top of the channel API by Subscription.Notify.
type Observer interface {
	OnQuote(Quote)
}

// ObserverFunc adapts a plain function to the Observer interface.
type ObserverFunc func(Quote)

// OnQuote calls f(q).
func (f ObserverFunc) OnQuote(q Quote) { f(q) }

// Subscription is one observer's connection to a Hub.
//
// Quotes flow publisher -> in (bounded queue) -> pump goroutine -> out.
// The pump is the only sender on out, so it can close out safely; publishers
// never touch a channel that can be closed, which rules out "send on closed
// channel" panics by construction.
type Subscription struct {
	hub     *Hub
	symbols map[string]struct{} // nil means every symbol
	policy  OverflowPolicy

	in      chan Quote    // never closed
	out     chan Quote    // closed by pump
	done    chan struct{} // closed by Cancel; stops pump and blocked publishers
	stopped chan struct{} // closed once pump has exited

	cancelOnce sync.Once
	delivered  atomic.Uint64
	dropped    atomic.Uint64
}

func newSubscription(h *Hub, opts Options) *Subscription {
	s := &Subscription{
		hub:     h,
		policy:  opts.Policy,
		in:      make(chan Quote, opts.Buffer),
		out:     make(chan Quote),
		done:    make(chan struct{}),
		stopped: make(chan struct{}),
	}
	if len(opts.Symbols) > 0 {
		s.symbols = make(map[string]struct{}, len(opts.Symbols))
		for _, sym := range opts.Symbols {
			s.symbols[sym] = struct{}{}
		}
	}
	go s.pump()
	return s
}

// C returns the channel quotes arrive on. It is closed after Cancel or
// Hub.Close, so ranging over it terminates cleanly.
func (s *Subscription) C() <-chan Quote { return s.out }

// Cancel unsubscribes. Queued quotes are discarded, any publisher blocked on
// this subscriber is released, and C is closed by the time Cancel returns.
// It is safe to call repeatedly, concurrently, and from the consumer itself.
func (s *Subscription) Cancel() {
	s.cancelOnce.Do(func() {
		s.hub.remove(s)
		close(s.done)
	})
	<-s.stopped
}

// Stats returns the current delivery counters.
func (s *Subscription) Stats() Stats {
	return Stats{Delivered: s.delivered.Load(), Dropped: s.dropped.Load()}
}

// Notify calls o for each quote on the caller's goroutine, returning when the
// subscription ends.
func (s *Subscription) Notify(o Observer) {
	for q := range s.out {
		o.OnQuote(q)
	}
}

func (s *Subscription) wants(symbol string) bool {
	if s.symbols == nil {
		return true
	}
	_, ok := s.symbols[symbol]
	return ok
}

// pump moves quotes from the queue to the consumer. Because it holds one
// quote while waiting on out, effective capacity is Buffer+1.
func (s *Subscription) pump() {
	defer close(s.stopped)
	defer close(s.out)
	for {
		select {
		case <-s.done:
			return
		case q := <-s.in:
			select {
			case s.out <- q:
				s.delivered.Add(1)
			case <-s.done:
				return
			}
		}
	}
}

// offer enqueues q according to the overflow policy. Only the Block policy
// can fail, when ctx ends first. A cancelled subscription accepts and ignores.
func (s *Subscription) offer(ctx context.Context, q Quote) error {
	switch s.policy {
	case DropNewest:
		select {
		case s.in <- q:
		case <-s.done:
		default:
			s.dropped.Add(1)
		}
	case DropOldest:
		for {
			select {
			case s.in <- q:
				return nil
			case <-s.done:
				return nil
			default:
			}
			// Full: make room and retry. The inner default covers the pump
			// or another publisher having emptied the queue in between, so
			// each pass makes progress and the loop cannot wedge.
			select {
			case <-s.in:
				s.dropped.Add(1)
			default:
			}
		}
	default: // Block; Subscribe rejects unknown policies.
		select {
		case s.in <- q:
		case <-s.done:
		case <-ctx.Done():
			return ctx.Err()
		}
	}
	return nil
}
