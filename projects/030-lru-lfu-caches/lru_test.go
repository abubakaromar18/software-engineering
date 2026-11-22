package cache

import (
	"errors"
	"slices"
	"testing"
)

func mustLRU[K comparable, V any](t *testing.T, capacity int, opts ...Option[K, V]) *LRU[K, V] {
	t.Helper()
	c, err := NewLRU(capacity, opts...)
	if err != nil {
		t.Fatalf("NewLRU(%d): %v", capacity, err)
	}
	return c
}

func TestNewRejectsBadCapacity(t *testing.T) {
	for _, capacity := range []int{0, -1} {
		if _, err := NewLRU[string, int](capacity); !errors.Is(err, ErrInvalidCapacity) {
			t.Errorf("NewLRU(%d) err = %v, want ErrInvalidCapacity", capacity, err)
		}
		if _, err := NewLFU[string, int](capacity); !errors.Is(err, ErrInvalidCapacity) {
			t.Errorf("NewLFU(%d) err = %v, want ErrInvalidCapacity", capacity, err)
		}
	}
}

func TestLRUEvictsLeastRecentlyUsed(t *testing.T) {
	c := mustLRU[string, int](t, 3)
	c.Put("a", 1)
	c.Put("b", 2)
	c.Put("c", 3)
	c.Get("a") // order now a c b; b is LRU

	if evicted := c.Put("d", 4); !evicted {
		t.Fatal("Put into full cache should report eviction")
	}
	if _, ok := c.Peek("b"); ok {
		t.Fatal("b should have been evicted")
	}
	if got, want := c.Keys(), []string{"d", "a", "c"}; !slices.Equal(got, want) {
		t.Fatalf("Keys = %v, want %v", got, want)
	}
}

func TestLRUUpdateRefreshesRecencyWithoutEviction(t *testing.T) {
	c := mustLRU[string, int](t, 2)
	c.Put("a", 1)
	c.Put("b", 2)
	if evicted := c.Put("a", 10); evicted {
		t.Fatal("updating an existing key must not evict")
	}
	c.Put("c", 3) // evicts b, since a was refreshed
	if v, ok := c.Get("a"); !ok || v != 10 {
		t.Fatalf("Get(a) = %v,%v want 10,true", v, ok)
	}
	if _, ok := c.Peek("b"); ok {
		t.Fatal("b should have been evicted")
	}
}

func TestLRUPeekDoesNotPromoteOrCount(t *testing.T) {
	c := mustLRU[string, int](t, 2)
	c.Put("a", 1)
	c.Put("b", 2)
	if v, ok := c.Peek("a"); !ok || v != 1 {
		t.Fatalf("Peek(a) = %v,%v", v, ok)
	}
	c.Put("c", 3) // a is still LRU despite the Peek
	if _, ok := c.Peek("a"); ok {
		t.Fatal("Peek must not change recency")
	}
	if s := c.Stats(); s.Hits != 0 || s.Misses != 0 {
		t.Fatalf("Peek must not touch stats: %+v", s)
	}
}

func TestLRUDelete(t *testing.T) {
	c := mustLRU[int, string](t, 2)
	c.Put(1, "one")
	if !c.Delete(1) || c.Delete(1) {
		t.Fatal("Delete should succeed once then report absence")
	}
	if c.Len() != 0 {
		t.Fatalf("Len = %d after delete", c.Len())
	}
	// Space freed by Delete is reusable without eviction.
	c.Put(2, "two")
	if c.Put(3, "three") {
		t.Fatal("no eviction expected after delete freed a slot")
	}
}

func TestLRUStatsAndCallback(t *testing.T) {
	var evicted []string
	c := mustLRU(t, 1, WithOnEvict(func(k string, v int) { evicted = append(evicted, k) }))
	c.Put("a", 1)
	c.Get("a")
	c.Get("missing")
	c.Put("b", 2)
	c.Delete("b") // deletes do not fire the callback

	want := Stats{Hits: 1, Misses: 1, Evictions: 1}
	if got := c.Stats(); got != want {
		t.Fatalf("Stats = %+v, want %+v", got, want)
	}
	if got := c.Stats().HitRatio(); got != 0.5 {
		t.Fatalf("HitRatio = %v", got)
	}
	if !slices.Equal(evicted, []string{"a"}) {
		t.Fatalf("callback saw %v", evicted)
	}
}

func TestStatsHitRatioEmpty(t *testing.T) {
	if r := (Stats{}).HitRatio(); r != 0 {
		t.Fatalf("empty HitRatio = %v", r)
	}
	if s := (Stats{Hits: 3, Misses: 1, Evictions: 2}).String(); s != "hits=3 misses=1 evictions=2 hit-ratio=75.00%" {
		t.Fatalf("String = %q", s)
	}
}
