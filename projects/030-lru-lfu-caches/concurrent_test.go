package cache

import (
	"errors"
	"sync"
	"sync/atomic"
	"testing"
)

func TestNewShardedValidation(t *testing.T) {
	cases := []struct {
		name         string
		shards, cap  int
		wantSentinel error
	}{
		{"zero capacity", 1, 0, ErrInvalidCapacity},
		{"zero shards", 0, 10, ErrInvalidShards},
		{"more shards than capacity", 11, 10, ErrInvalidShards},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := NewShardedLRU[int, int](tc.shards, tc.cap); !errors.Is(err, tc.wantSentinel) {
				t.Fatalf("err = %v, want %v", err, tc.wantSentinel)
			}
		})
	}
}

func TestNewShardedPropagatesFactoryError(t *testing.T) {
	boom := errors.New("boom")
	_, err := NewSharded(2, 4, func(int) (Cache[int, int], error) { return nil, boom })
	if !errors.Is(err, boom) {
		t.Fatalf("err = %v, want wrapped boom", err)
	}
}

func TestShardedSplitsCapacityExactly(t *testing.T) {
	s, err := NewShardedLFU[int, int](3, 10)
	if err != nil {
		t.Fatal(err)
	}
	if s.Cap() != 10 || s.Shards() != 3 {
		t.Fatalf("Cap=%d Shards=%d", s.Cap(), s.Shards())
	}
	for i := range 1000 {
		s.Put(i, i)
	}
	if s.Len() != 10 {
		t.Fatalf("Len = %d after overfilling, want 10", s.Len())
	}
	if st := s.Stats(); st.Evictions != 990 {
		t.Fatalf("Evictions = %d, want 990", st.Evictions)
	}
}

func TestShardedRoutesKeysConsistently(t *testing.T) {
	s, err := NewShardedLRU[string, int](8, 64)
	if err != nil {
		t.Fatal(err)
	}
	s.Put("k", 7)
	if v, ok := s.Get("k"); !ok || v != 7 {
		t.Fatalf("Get = %d,%v", v, ok)
	}
	if v, ok := s.Peek("k"); !ok || v != 7 {
		t.Fatalf("Peek = %d,%v", v, ok)
	}
	if !s.Delete("k") {
		t.Fatal("Delete failed")
	}
	if _, ok := s.Get("k"); ok {
		t.Fatal("key still present after delete")
	}
}

func TestGetOrLoad(t *testing.T) {
	lru, _ := NewLRU[string, int](4)
	c := NewSynchronized[string, int](lru)
	calls := 0
	load := func(k string) (int, error) { calls++; return len(k), nil }

	for range 3 {
		if v, err := c.GetOrLoad("abc", load); err != nil || v != 3 {
			t.Fatalf("GetOrLoad = %d,%v", v, err)
		}
	}
	if calls != 1 {
		t.Fatalf("loader called %d times, want 1", calls)
	}

	boom := errors.New("backend down")
	if _, err := c.GetOrLoad("x", func(string) (int, error) { return 0, boom }); !errors.Is(err, boom) {
		t.Fatalf("err = %v", err)
	}
	if _, ok := c.Peek("x"); ok {
		t.Fatal("failed load must not be cached")
	}
}

// TestConcurrentAccess hammers both wrappers from many goroutines. Its main
// job is to give the race detector (`go test -race`) something to find; it
// also checks the invariants that must hold however operations interleave.
func TestConcurrentAccess(t *testing.T) {
	const (
		workers  = 16
		opsEach  = 2000
		capacity = 128
	)
	lfu, _ := NewLFU[int, int](capacity)
	sharded, _ := NewShardedLRU[int, int](8, capacity)
	caches := map[string]Cache[int, int]{
		"synchronized-lfu": NewSynchronized[int, int](lfu),
		"sharded-lru":      sharded,
	}
	for name, c := range caches {
		t.Run(name, func(t *testing.T) {
			var gets atomic.Uint64
			var wg sync.WaitGroup
			for w := range workers {
				wg.Add(1)
				go func() {
					defer wg.Done()
					for i := range opsEach {
						k := (w*7 + i) % (capacity * 2)
						switch i % 4 {
						case 0:
							c.Put(k, k)
						case 3:
							c.Delete(k)
						default:
							gets.Add(1)
							if v, ok := c.Get(k); ok && v != k {
								t.Errorf("Get(%d) = %d: value from another key", k, v)
							}
						}
					}
				}()
			}
			wg.Wait()

			if c.Len() > c.Cap() {
				t.Fatalf("Len %d exceeds Cap %d", c.Len(), c.Cap())
			}
			if st := c.Stats(); st.Hits+st.Misses != gets.Load() {
				t.Fatalf("hits+misses = %d, want %d gets", st.Hits+st.Misses, gets.Load())
			}
		})
	}
}
