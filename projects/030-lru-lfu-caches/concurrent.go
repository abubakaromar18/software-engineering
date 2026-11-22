package cache

import (
	"errors"
	"fmt"
	"hash/maphash"
	"sync"
)

// Synchronized makes any Cache safe for concurrent use with one mutex.
//
// A plain Mutex is used rather than an RWMutex because every Get mutates the
// policy's bookkeeping (recency list or frequency buckets), so there are no
// read-only fast paths to share.
type Synchronized[K comparable, V any] struct {
	mu    sync.Mutex
	inner Cache[K, V]
}

var _ Cache[string, int] = (*Synchronized[string, int])(nil)

// NewSynchronized wraps inner. The caller must not use inner directly
// afterwards, or the lock is bypassed.
func NewSynchronized[K comparable, V any](inner Cache[K, V]) *Synchronized[K, V] {
	return &Synchronized[K, V]{inner: inner}
}

func (s *Synchronized[K, V]) Get(key K) (V, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.inner.Get(key)
}

func (s *Synchronized[K, V]) Peek(key K) (V, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.inner.Peek(key)
}

func (s *Synchronized[K, V]) Put(key K, value V) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.inner.Put(key, value)
}

func (s *Synchronized[K, V]) Delete(key K) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.inner.Delete(key)
}

func (s *Synchronized[K, V]) Len() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.inner.Len()
}

// Cap does not lock: capacity is fixed at construction.
func (s *Synchronized[K, V]) Cap() int { return s.inner.Cap() }

func (s *Synchronized[K, V]) Stats() Stats {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.inner.Stats()
}

// GetOrLoad returns the cached value for key, or calls load, stores its result
// and returns it. The lock is held while load runs, so concurrent callers for
// the same key never load twice; the price is that a slow load blocks every
// other operation on this cache (or shard). If load fails nothing is stored.
func (s *Synchronized[K, V]) GetOrLoad(key K, load func(K) (V, error)) (V, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if v, ok := s.inner.Get(key); ok {
		return v, nil
	}
	v, err := load(key)
	if err != nil {
		var zero V
		return zero, err
	}
	s.inner.Put(key, v)
	return v, nil
}

// ErrInvalidShards is returned when shard count is < 1 or exceeds capacity.
var ErrInvalidShards = errors.New("cache: shard count must be between 1 and capacity")

// Sharded spreads keys across independently locked caches chosen by hashing
// the key, so goroutines touching different shards do not contend.
//
// The trade-off is that eviction becomes per-shard: the policy is exact within
// a shard but only approximate across the whole cache (a hot shard may evict
// an entry that is "better" than a cold shard's worst one). With a good hash
// and many keys the difference in hit ratio is small.
type Sharded[K comparable, V any] struct {
	seed   maphash.Seed
	shards []*Synchronized[K, V] // separate allocations, so locks rarely share a cache line
}

var _ Cache[string, int] = (*Sharded[string, int])(nil)

// NewSharded builds a cache of total capacity split across n shards, using
// newShard to construct each one. Capacity is divided as evenly as possible.
func NewSharded[K comparable, V any](n, capacity int, newShard func(capacity int) (Cache[K, V], error)) (*Sharded[K, V], error) {
	if capacity < 1 {
		return nil, fmt.Errorf("%w (got %d)", ErrInvalidCapacity, capacity)
	}
	if n < 1 || n > capacity {
		return nil, fmt.Errorf("%w (got %d shards for capacity %d)", ErrInvalidShards, n, capacity)
	}
	s := &Sharded[K, V]{seed: maphash.MakeSeed(), shards: make([]*Synchronized[K, V], n)}
	base, extra := capacity/n, capacity%n
	for i := range s.shards {
		c := base
		if i < extra {
			c++
		}
		inner, err := newShard(c)
		if err != nil {
			return nil, fmt.Errorf("cache: creating shard %d: %w", i, err)
		}
		s.shards[i] = NewSynchronized(inner)
	}
	return s, nil
}

// NewShardedLRU is NewSharded with an LRU in every shard.
func NewShardedLRU[K comparable, V any](n, capacity int, opts ...Option[K, V]) (*Sharded[K, V], error) {
	return NewSharded(n, capacity, func(c int) (Cache[K, V], error) { return NewLRU(c, opts...) })
}

// NewShardedLFU is NewSharded with an LFU in every shard.
func NewShardedLFU[K comparable, V any](n, capacity int, opts ...Option[K, V]) (*Sharded[K, V], error) {
	return NewSharded(n, capacity, func(c int) (Cache[K, V], error) { return NewLFU(c, opts...) })
}

func (s *Sharded[K, V]) shard(key K) *Synchronized[K, V] {
	h := maphash.Comparable(s.seed, key)
	return s.shards[h%uint64(len(s.shards))]
}

func (s *Sharded[K, V]) Get(key K) (V, bool)     { return s.shard(key).Get(key) }
func (s *Sharded[K, V]) Peek(key K) (V, bool)    { return s.shard(key).Peek(key) }
func (s *Sharded[K, V]) Put(key K, value V) bool { return s.shard(key).Put(key, value) }
func (s *Sharded[K, V]) Delete(key K) bool       { return s.shard(key).Delete(key) }
func (s *Sharded[K, V]) GetOrLoad(key K, load func(K) (V, error)) (V, error) {
	return s.shard(key).GetOrLoad(key, load)
}

// Len sums shard lengths. Shards are locked one at a time, so under concurrent
// writes the result is a close approximation rather than a point-in-time value.
func (s *Sharded[K, V]) Len() int {
	total := 0
	for _, sh := range s.shards {
		total += sh.Len()
	}
	return total
}

func (s *Sharded[K, V]) Cap() int {
	total := 0
	for _, sh := range s.shards {
		total += sh.Cap()
	}
	return total
}

// Stats aggregates shard counters, with the same caveat as Len.
func (s *Sharded[K, V]) Stats() Stats {
	var total Stats
	for _, sh := range s.shards {
		total = total.add(sh.Stats())
	}
	return total
}

// Shards returns the number of shards.
func (s *Sharded[K, V]) Shards() int { return len(s.shards) }
