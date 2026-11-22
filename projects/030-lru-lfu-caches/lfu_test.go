package cache

import (
	"slices"
	"testing"
)

func mustLFU[K comparable, V any](t *testing.T, capacity int, opts ...Option[K, V]) *LFU[K, V] {
	t.Helper()
	c, err := NewLFU(capacity, opts...)
	if err != nil {
		t.Fatalf("NewLFU(%d): %v", capacity, err)
	}
	return c
}

func TestLFUEvictsLeastFrequentlyUsed(t *testing.T) {
	c := mustLFU[string, int](t, 3)
	c.Put("a", 1)
	c.Put("b", 2)
	c.Put("c", 3)
	c.Get("a")
	c.Get("a")
	c.Get("c") // freqs: a=3 c=2 b=1

	c.Put("d", 4) // evicts b
	if _, ok := c.Peek("b"); ok {
		t.Fatal("b (freq 1) should have been evicted")
	}
	if got, want := c.Keys(), []string{"a", "c", "d"}; !slices.Equal(got, want) {
		t.Fatalf("Keys = %v, want %v", got, want)
	}
}

func TestLFUTieBreaksByRecency(t *testing.T) {
	c := mustLFU[string, int](t, 2)
	c.Put("a", 1)
	c.Put("b", 2) // both freq 1; a is older
	c.Put("c", 3)
	if _, ok := c.Peek("a"); ok {
		t.Fatal("a should be evicted: same frequency as b but less recent")
	}
}

func TestLFUPutOnExistingKeyCountsAsAccess(t *testing.T) {
	c := mustLFU[string, int](t, 2)
	c.Put("a", 1)
	c.Put("a", 2)
	if f, _ := c.Frequency("a"); f != 2 {
		t.Fatalf("Frequency(a) = %d, want 2", f)
	}
	if v, _ := c.Peek("a"); v != 2 {
		t.Fatalf("value not updated: %d", v)
	}
	if f, _ := c.Frequency("a"); f != 2 {
		t.Fatal("Peek must not change frequency")
	}
}

func TestLFUNewEntryStartsAtOneAfterEviction(t *testing.T) {
	c := mustLFU[int, int](t, 2)
	c.Put(1, 1)
	c.Put(2, 2)
	for range 5 {
		c.Get(1)
		c.Get(2)
	}
	c.Put(3, 3) // evicts 1 (tie at 6; 1 is less recent)
	if f, ok := c.Frequency(3); !ok || f != 1 {
		t.Fatalf("Frequency(3) = %d,%v want 1,true", f, ok)
	}
	// 3 is now the only freq-1 entry and therefore the next victim, even
	// though it is the most recent: frequency dominates recency.
	c.Put(4, 4)
	if _, ok := c.Peek(3); ok {
		t.Fatal("3 should be evicted before high-frequency 2")
	}
}

func TestLFUDeleteFromMiddleBucket(t *testing.T) {
	c := mustLFU[string, int](t, 3)
	c.Put("a", 1) // a=1
	c.Put("b", 2)
	c.Get("b") // b=2
	c.Put("c", 3)
	c.Get("c")
	c.Get("c") // c=3

	if !c.Delete("b") { // freq-2 bucket becomes empty and must be unlinked
		t.Fatal("Delete(b) failed")
	}
	c.Get("a") // a moves 1 -> 2: a new bucket is inserted before freq 3
	if f, _ := c.Frequency("a"); f != 2 {
		t.Fatalf("Frequency(a) = %d", f)
	}
	if got, want := c.Keys(), []string{"c", "a"}; !slices.Equal(got, want) {
		t.Fatalf("Keys = %v, want %v", got, want)
	}
	if c.Delete("zzz") {
		t.Fatal("Delete of missing key should return false")
	}
}

func TestLFUCallbackAndStats(t *testing.T) {
	type pair struct {
		k string
		v int
	}
	var seen []pair
	c := mustLFU(t, 1, WithOnEvict(func(k string, v int) { seen = append(seen, pair{k, v}) }))
	c.Put("a", 1)
	c.Put("b", 2)
	c.Get("a")
	c.Get("b")
	if want := []pair{{"a", 1}}; !slices.Equal(seen, want) {
		t.Fatalf("evicted %v, want %v", seen, want)
	}
	if got, want := c.Stats(), (Stats{Hits: 1, Misses: 1, Evictions: 1}); got != want {
		t.Fatalf("Stats = %+v, want %+v", got, want)
	}
	if c.Len() != 1 || c.Cap() != 1 {
		t.Fatalf("Len/Cap = %d/%d", c.Len(), c.Cap())
	}
}
