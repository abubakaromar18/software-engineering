// Package cache provides bounded, generic in-memory caches with O(1)
// operations:
//
//   - LRU evicts the least recently used entry.
//   - LFU evicts the least frequently used entry, breaking ties by recency
//     (the O(1) bucket design of Shah, Mitra & Matani, 2010).
//
// LRU and LFU are deliberately not safe for concurrent use: most callers own a
// cache from one goroutine and should not pay for locking. Wrap a cache in
// Synchronized for a single lock, or use Sharded to spread contention across
// several independently locked caches.
package cache

import (
	"errors"
	"fmt"
)

// ErrInvalidCapacity is returned when a cache is created with capacity < 1.
var ErrInvalidCapacity = errors.New("cache: capacity must be at least 1")

// Cache is the behaviour shared by every cache in this package, which lets
// the concurrent wrappers and the simulator treat policies interchangeably.
type Cache[K comparable, V any] interface {
	// Get returns the value for key and records an access (which may change
	// eviction order) and a hit or miss.
	Get(key K) (V, bool)
	// Peek returns the value for key without recording an access or stats.
	Peek(key K) (V, bool)
	// Put inserts or updates key. It reports whether another entry was
	// evicted to make room.
	Put(key K, value V) (evicted bool)
	// Delete removes key and reports whether it was present.
	Delete(key K) bool
	// Len is the number of entries currently stored.
	Len() int
	// Cap is the maximum number of entries.
	Cap() int
	// Stats returns a snapshot of the hit/miss/eviction counters.
	Stats() Stats
}

// Stats counts cache outcomes. Only Get affects Hits and Misses; only
// capacity-driven removals count as Evictions.
type Stats struct {
	Hits      uint64
	Misses    uint64
	Evictions uint64
}

// HitRatio returns Hits / (Hits + Misses), or 0 if there were no lookups.
func (s Stats) HitRatio() float64 {
	total := s.Hits + s.Misses
	if total == 0 {
		return 0
	}
	return float64(s.Hits) / float64(total)
}

// add returns the element-wise sum, used to aggregate shard statistics.
func (s Stats) add(o Stats) Stats {
	return Stats{Hits: s.Hits + o.Hits, Misses: s.Misses + o.Misses, Evictions: s.Evictions + o.Evictions}
}

func (s Stats) String() string {
	return fmt.Sprintf("hits=%d misses=%d evictions=%d hit-ratio=%.2f%%",
		s.Hits, s.Misses, s.Evictions, 100*s.HitRatio())
}

// config holds optional settings shared by all policies.
type config[K comparable, V any] struct {
	onEvict func(K, V)
}

// Option configures a cache at construction time.
type Option[K comparable, V any] func(*config[K, V])

// WithOnEvict registers fn to be called with each entry evicted for capacity.
// It is not called for Delete or for overwriting an existing key.
//
// fn runs synchronously inside the cache operation (and, for the concurrent
// wrappers, while the lock is held), so it must be quick and must not call
// back into the same cache.
func WithOnEvict[K comparable, V any](fn func(key K, value V)) Option[K, V] {
	return func(c *config[K, V]) { c.onEvict = fn }
}

func buildConfig[K comparable, V any](capacity int, opts []Option[K, V]) (config[K, V], error) {
	var cfg config[K, V]
	if capacity < 1 {
		return cfg, fmt.Errorf("%w (got %d)", ErrInvalidCapacity, capacity)
	}
	for _, opt := range opts {
		opt(&cfg)
	}
	return cfg, nil
}
