package ticker

import (
	"context"
	"errors"
	"fmt"
	"sync"
)

// DefaultBuffer is the queue size used when Options.Buffer is zero.
const DefaultBuffer = 16

// ErrClosed is returned by Publish and Subscribe after Hub.Close.
var ErrClosed = errors.New("ticker: hub closed")

// Options configures a subscription.
type Options struct {
	Buffer  int            // queue size; 0 means DefaultBuffer
	Policy  OverflowPolicy // zero value is Block
	Symbols []string       // empty means every symbol
}

func (o Options) normalized() (Options, error) {
	if o.Buffer < 0 {
		return o, fmt.Errorf("ticker: buffer must not be negative, got %d", o.Buffer)
	}
	if o.Buffer == 0 {
		o.Buffer = DefaultBuffer
	}
	if o.Policy < Block || o.Policy > DropNewest {
		return o, fmt.Errorf("ticker: unknown overflow policy %v", o.Policy)
	}
	return o, nil
}

// Hub fans quotes out to subscribers. All methods are safe for concurrent use.
//
// The subscriber list is copy-on-write: Publish reads an immutable slice and
// delivers without holding the lock, so a publisher blocked on a slow
// subscriber can never prevent that subscriber from cancelling.
type Hub struct {
	mu     sync.RWMutex
	subs   []*Subscription
	closed bool
}

// NewHub returns an empty, open Hub.
func NewHub() *Hub { return &Hub{} }

// Subscribe registers a new subscriber. Call Cancel when finished with it.
func (h *Hub) Subscribe(opts Options) (*Subscription, error) {
	opts, err := opts.normalized()
	if err != nil {
		return nil, err
	}
	h.mu.Lock()
	defer h.mu.Unlock()
	if h.closed {
		return nil, ErrClosed
	}
	s := newSubscription(h, opts)
	next := make([]*Subscription, len(h.subs), len(h.subs)+1)
	copy(next, h.subs)
	h.subs = append(next, s)
	return s, nil
}

// Publish offers q to every interested subscriber, in subscription order.
//
// It returns early with ctx's error if a Block subscriber holds it up past
// ctx's end; subscribers earlier in the order will already have q. Ordering is
// guaranteed per publisher: concurrent publishers may interleave.
func (h *Hub) Publish(ctx context.Context, q Quote) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	h.mu.RLock()
	subs, closed := h.subs, h.closed
	h.mu.RUnlock()
	if closed {
		return ErrClosed
	}
	for _, s := range subs {
		if !s.wants(q.Symbol) {
			continue
		}
		if err := s.offer(ctx, q); err != nil {
			return fmt.Errorf("ticker: publish %s seq %d: %w", q.Symbol, q.Seq, err)
		}
	}
	return nil
}

// Close cancels every subscription and rejects further use. It is idempotent.
func (h *Hub) Close() {
	h.mu.Lock()
	subs := h.subs
	h.subs = nil
	h.closed = true
	h.mu.Unlock()

	// Outside the lock, because Cancel re-enters the hub through remove.
	for _, s := range subs {
		s.Cancel()
	}
}

func (h *Hub) remove(target *Subscription) {
	h.mu.Lock()
	defer h.mu.Unlock()
	for i, s := range h.subs {
		if s == target {
			next := make([]*Subscription, 0, len(h.subs)-1)
			next = append(next, h.subs[:i]...)
			h.subs = append(next, h.subs[i+1:]...)
			return
		}
	}
}
