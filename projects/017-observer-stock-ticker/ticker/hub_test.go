package ticker

import (
	"context"
	"errors"
	"runtime"
	"sync"
	"testing"
	"time"
)

const testTimeout = 5 * time.Second

func newSub(t *testing.T, h *Hub, o Options) *Subscription {
	t.Helper()
	s, err := h.Subscribe(o)
	if err != nil {
		t.Fatalf("Subscribe: %v", err)
	}
	t.Cleanup(s.Cancel)
	return s
}

func publish(t *testing.T, h *Hub, symbol string, seqs ...uint64) {
	t.Helper()
	for _, n := range seqs {
		if err := h.Publish(context.Background(), Quote{Symbol: symbol, Seq: n}); err != nil {
			t.Fatalf("Publish(%d): %v", n, err)
		}
	}
}

func seqRange(from, to uint64) []uint64 {
	out := make([]uint64, 0, to-from+1)
	for n := from; n <= to; n++ {
		out = append(out, n)
	}
	return out
}

func recv(t *testing.T, s *Subscription) Quote {
	t.Helper()
	select {
	case q, ok := <-s.C():
		if !ok {
			t.Fatal("channel closed while waiting for a quote")
		}
		return q
	case <-time.After(testTimeout):
		t.Fatal("timed out waiting for a quote")
	}
	return Quote{}
}

func waitClosed(t *testing.T, s *Subscription) {
	t.Helper()
	timeout := time.After(testTimeout)
	for {
		select {
		case _, ok := <-s.C():
			if !ok {
				return
			}
		case <-timeout:
			t.Fatal("channel was not closed")
		}
	}
}

// drainAccounted reads until every published quote is either received or
// counted as dropped, which is the invariant all lossy policies must keep.
func drainAccounted(t *testing.T, s *Subscription, published uint64) []uint64 {
	t.Helper()
	var got []uint64
	for uint64(len(got))+s.Stats().Dropped < published {
		got = append(got, recv(t, s).Seq)
	}
	return got
}

func assertIncreasing(t *testing.T, seqs []uint64) {
	t.Helper()
	for i := 1; i < len(seqs); i++ {
		if seqs[i] <= seqs[i-1] {
			t.Fatalf("out of order at %d: %v", i, seqs)
		}
	}
}

func TestFanOutDeliversInOrderToEverySubscriber(t *testing.T) {
	h := NewHub()
	a, b := newSub(t, h, Options{}), newSub(t, h, Options{})
	publish(t, h, "ACME", 1, 2, 3)
	for _, s := range []*Subscription{a, b} {
		for want := uint64(1); want <= 3; want++ {
			if got := recv(t, s).Seq; got != want {
				t.Fatalf("seq = %d, want %d", got, want)
			}
		}
	}
}

func TestSymbolFilter(t *testing.T) {
	h := NewHub()
	s := newSub(t, h, Options{Symbols: []string{"ACME"}})
	publish(t, h, "OTHER", 1)
	publish(t, h, "ACME", 2)
	if q := recv(t, s); q.Seq != 2 || q.Symbol != "ACME" {
		t.Fatalf("got %+v", q)
	}
}

func TestCancelClosesChannelStopsDeliveryAndIsIdempotent(t *testing.T) {
	h := NewHub()
	gone, kept := newSub(t, h, Options{}), newSub(t, h, Options{})
	gone.Cancel()
	gone.Cancel()
	if _, ok := <-gone.C(); ok {
		t.Fatal("expected a closed channel straight after Cancel")
	}
	publish(t, h, "ACME", 1)
	if recv(t, kept).Seq != 1 {
		t.Fatal("remaining subscriber missed the quote")
	}
	if got := gone.Stats().Delivered; got != 0 {
		t.Fatalf("cancelled subscriber delivered %d", got)
	}
}

func TestBlockPolicyIsLosslessAndHonoursContext(t *testing.T) {
	h := NewHub()
	s := newSub(t, h, Options{Buffer: 1, Policy: Block})

	var published uint64
	for {
		ctx, cancel := context.WithTimeout(context.Background(), 20*time.Millisecond)
		err := h.Publish(ctx, Quote{Symbol: "ACME", Seq: published + 1})
		cancel()
		if errors.Is(err, context.DeadlineExceeded) {
			break
		}
		if err != nil {
			t.Fatalf("Publish: %v", err)
		}
		if published++; published > 10 {
			t.Fatal("publisher never blocked on a full subscriber")
		}
	}
	for want := uint64(1); want <= published; want++ {
		if got := recv(t, s).Seq; got != want {
			t.Fatalf("seq = %d, want %d", got, want)
		}
	}
	if d := s.Stats().Dropped; d != 0 {
		t.Fatalf("Block dropped %d quotes", d)
	}
}

func TestCancelReleasesBlockedPublisher(t *testing.T) {
	h := NewHub()
	s := newSub(t, h, Options{Buffer: 1, Policy: Block})
	finished := make(chan error, 1)
	go func() {
		var err error
		for n := uint64(1); n <= 5 && err == nil; n++ {
			err = h.Publish(context.Background(), Quote{Symbol: "ACME", Seq: n})
		}
		finished <- err
	}()
	time.Sleep(20 * time.Millisecond) // let the publisher reach the full queue
	s.Cancel()
	select {
	case err := <-finished:
		if err != nil {
			t.Fatalf("publisher got %v", err)
		}
	case <-time.After(testTimeout):
		t.Fatal("Cancel did not release the blocked publisher")
	}
}

func TestDropOldestKeepsTheNewestQuote(t *testing.T) {
	const n = 100
	h := NewHub()
	s := newSub(t, h, Options{Buffer: 2, Policy: DropOldest})
	publish(t, h, "ACME", seqRange(1, n)...)

	got := drainAccounted(t, s, n)
	assertIncreasing(t, got)
	if len(got) == 0 || got[len(got)-1] != n {
		t.Fatalf("newest quote lost: %v", got)
	}
	if s.Stats().Dropped == 0 {
		t.Fatal("expected drops on an unread subscriber")
	}
}

func TestDropNewestKeepsTheOldestQuotes(t *testing.T) {
	const n = 100
	h := NewHub()
	s := newSub(t, h, Options{Buffer: 2, Policy: DropNewest})
	publish(t, h, "ACME", seqRange(1, n)...)

	got := drainAccounted(t, s, n)
	assertIncreasing(t, got)
	if len(got) == 0 || got[0] != 1 {
		t.Fatalf("oldest quote lost: %v", got)
	}
	if len(got) > 3 { // Buffer + the one held by the pump
		t.Fatalf("received %d quotes, capacity is 3", len(got))
	}
}

func TestLossySlowSubscriberDoesNotStallOthers(t *testing.T) {
	const n = 500
	h := NewHub()
	newSub(t, h, Options{Buffer: 1, Policy: DropNewest}) // never read
	fast := newSub(t, h, Options{Buffer: 1, Policy: Block})

	received := make(chan int, 1)
	go func() {
		count := 0
		for range fast.C() {
			if count++; count == n {
				break
			}
		}
		received <- count
	}()
	publish(t, h, "ACME", seqRange(1, n)...)
	select {
	case got := <-received:
		if got != n {
			t.Fatalf("fast subscriber received %d of %d", got, n)
		}
	case <-time.After(testTimeout):
		t.Fatal("fast subscriber was stalled")
	}
}

func TestCloseEndsSubscriptionsAndRejectsUse(t *testing.T) {
	h := NewHub()
	s := newSub(t, h, Options{})
	h.Close()
	h.Close()
	waitClosed(t, s)
	if err := h.Publish(context.Background(), Quote{}); !errors.Is(err, ErrClosed) {
		t.Fatalf("Publish after Close: %v", err)
	}
	if _, err := h.Subscribe(Options{}); !errors.Is(err, ErrClosed) {
		t.Fatalf("Subscribe after Close: %v", err)
	}
}

func TestPublishWithCancelledContextFailsFast(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if err := NewHub().Publish(ctx, Quote{}); !errors.Is(err, context.Canceled) {
		t.Fatalf("got %v", err)
	}
}

func TestSubscribeRejectsInvalidOptions(t *testing.T) {
	h := NewHub()
	for name, o := range map[string]Options{
		"negative buffer": {Buffer: -1},
		"unknown policy":  {Policy: OverflowPolicy(99)},
	} {
		if _, err := h.Subscribe(o); err == nil {
			t.Errorf("%s: expected an error", name)
		}
	}
}

func TestNotifyCallsObserverUntilCancelled(t *testing.T) {
	h := NewHub()
	s := newSub(t, h, Options{})
	seen := make(chan uint64, 1)
	finished := make(chan struct{})
	go func() {
		defer close(finished)
		s.Notify(ObserverFunc(func(q Quote) { seen <- q.Seq }))
	}()
	publish(t, h, "ACME", 7)
	if got := <-seen; got != 7 {
		t.Fatalf("seq = %d", got)
	}
	s.Cancel()
	select {
	case <-finished:
	case <-time.After(testTimeout):
		t.Fatal("Notify did not return after Cancel")
	}
}

// TestConcurrentChurn exists mainly for -race: publishers and subscribers
// come and go together, and nothing may panic, deadlock, or leak.
func TestConcurrentChurn(t *testing.T) {
	baseline := runtime.NumGoroutine()
	h := NewHub()
	ctx, cancel := context.WithTimeout(context.Background(), testTimeout)
	defer cancel()

	var wg sync.WaitGroup
	for p := 0; p < 4; p++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for n := uint64(0); n < 2000; n++ {
				if err := h.Publish(ctx, Quote{Symbol: "ACME", Seq: n}); err != nil {
					t.Errorf("Publish: %v", err)
					return
				}
			}
		}()
	}
	for c := 0; c < 8; c++ {
		wg.Add(1)
		go func(c int) {
			defer wg.Done()
			for i := 0; i < 50; i++ {
				s, err := h.Subscribe(Options{Buffer: 1 + c, Policy: OverflowPolicy(c % 3)})
				if err != nil {
					t.Errorf("Subscribe: %v", err)
					return
				}
				select {
				case <-s.C():
				case <-time.After(time.Millisecond):
				}
				s.Cancel()
			}
		}(c)
	}
	wg.Wait()
	h.Close()

	deadline := time.Now().Add(testTimeout)
	for runtime.NumGoroutine() > baseline {
		if time.Now().After(deadline) {
			t.Fatalf("goroutines leaked: %d > %d", runtime.NumGoroutine(), baseline)
		}
		time.Sleep(5 * time.Millisecond)
	}
}

func TestCentsString(t *testing.T) {
	for c, want := range map[Cents]string{0: "0.00", 5: "0.05", 18705: "187.05", -150: "-1.50"} {
		if got := c.String(); got != want {
			t.Errorf("Cents(%d) = %q, want %q", int64(c), got, want)
		}
	}
}
